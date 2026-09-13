/**
 * Adaptador del backend REAL de NextMove — subsistema /app/* (ver
 * backend/app_router.py). A diferencia de la versión anterior, este
 * adaptador YA NO delega el flujo interactivo a mockApi: llama de verdad a
 * los endpoints /app/sessions/*, que son la fuente de verdad para
 * disponibilidad, restricciones, puntuación y rutas (secciones 4 y 22 del
 * brief). El frontend solo pide, muestra y envía la acción del usuario.
 *
 * Si el backend no responde, este adaptador NO cae en silencio a datos
 * simulados (eso ocultaría fallas reales, sección 19) — deja que el error
 * se propague para que useSession.ts lo muestre como una notificación.
 */
import { API_URL, REQUEST_TIMEOUT_MS, VEHICLE_PROFILES } from "../constants/config";
import { AcceptResult, AppEvent, DataProvider, TickResult } from "../types/api";
import { CompletedDelivery, OrderOffer } from "../types/order";
import { RouteData, RoutePlan, RouteSegment } from "../types/route";
import { SessionConfig, SessionTotals } from "../types/session";

class ApiError extends Error {}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let resp: Response;
  try {
    resp = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
  } catch (err) {
    clearTimeout(timer);
    throw new ApiError(
      `We couldn't reach the server. Make sure the backend is running and reachable at ${API_URL}.`
    );
  }
  clearTimeout(timer);
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new ApiError(`Server error (${resp.status}). ${text}`.trim());
  }
  if (resp.status === 204) return undefined as unknown as T;
  return resp.json() as Promise<T>;
}

function toRoutePlan(route: RouteData | null | undefined): RoutePlan | null {
  if (!route) return null;
  return { segments: route.segments as RouteSegment[], directSegment: null, provider: route.provider };
}

// Metadatos que el backend no devuelve en cada respuesta (p. ej. hora de
// inicio de la sesión, nombre del restaurante activo) pero que el frontend
// necesita para mostrar el resumen. Se guardan aquí, indexados por
// sessionId, para no inventarlos ni pedirle al backend campos que no
// forman parte de su contrato.
interface SessionMeta {
  startedAt: string;
  activeOfferMeta?: { restaurantName: string; additionalTimeMin: number };
}
const sessionMeta = new Map<string, SessionMeta>();

export const api: DataProvider = {
  isMock: false,

  async checkConnection() {
    try {
      const resp = await fetch(`${API_URL}/health`);
      return resp.ok;
    } catch {
      return false;
    }
  },

  async startSession(config: SessionConfig) {
    const data = await request<{ sessionId: string }>("/app/sessions", {
      method: "POST",
      body: JSON.stringify({
        currentLocation: config.currentLocation,
        destination: config.destination,
        deadline: config.deadline,
        flexibility: config.flexibility,
        vehicle: config.vehicle,
      }),
    });
    sessionMeta.set(data.sessionId, { startedAt: new Date().toISOString() });
    return data;
  },

  async endSession(sessionId) {
    sessionMeta.delete(sessionId);
    try {
      await request(`/app/sessions/${sessionId}`, { method: "DELETE" });
    } catch {
      // best-effort: si el backend ya no responde, igual limpiamos localmente
    }
  },

  async searchOrders(sessionId) {
    const recs = await request<any[]>(`/app/sessions/${sessionId}/recommendations`);
    return recs.map((r): OrderOffer => {
      const segs: RouteSegment[] = r.route.segments;
      const pickupCoord = segs[0]?.coordinates[segs[0].coordinates.length - 1];
      const dropoffCoord = segs[1]?.coordinates[segs[1].coordinates.length - 1];
      const createdAt = new Date(new Date(r.expiresAt).getTime() - 60000).toISOString();
      return {
        id: r.orderId,
        restaurantName: r.restaurantName,
        dropoffLabel: r.dropoffName,
        netEarnings: r.netEarningsMxn,
        grossPay: r.grossPayMxn,
        extraMinutes: r.additionalTimeMin,
        extraKm: r.additionalDistanceKm,
        etaAtDestination: r.finalArrivalTime,
        reasonShort: r.reason,
        prepTimeMin: 8, // el backend real no separa el tiempo de preparación; valor razonable por defecto
        createdAt,
        expiresAt: r.expiresAt,
        pickup: pickupCoord ? { ...pickupCoord, label: r.pickupName } : { latitude: 0, longitude: 0, label: r.pickupName },
        dropoff: dropoffCoord ? { ...dropoffCoord, label: r.dropoffName } : { latitude: 0, longitude: 0, label: r.dropoffName },
        status: r.available ? "available" : "expired",
        orderNumber: `#${r.orderId.replace("ORD-", "")}`,
      };
    });
  },

  async refreshOffer(sessionId, offerId) {
    // El backend no expone un GET de una sola oferta; releemos toda la
    // lista (barata: son 3 ofertas) y buscamos la que nos interesa.
    const offers = await this.searchOrders(sessionId);
    return offers.find((o) => o.id === offerId) ?? null;
  },

  async acceptOffer(sessionId, offerId): Promise<AcceptResult> {
    const body = await request<any>(`/app/sessions/${sessionId}/orders/${offerId}/accept`, { method: "POST" });
    if (body.success) {
      const meta = sessionMeta.get(sessionId);
      if (meta) {
        // Guardamos metadatos del pedido activo para poder completar el
        // resumen de entrega más adelante (el backend no los repite en /delivery).
        const offers = await this.searchOrders(sessionId).catch(() => []);
        const matching = offers.find((o) => o.id === offerId);
        meta.activeOfferMeta = matching
          ? { restaurantName: matching.restaurantName, additionalTimeMin: matching.extraMinutes }
          : undefined;
      }
    }
    return { success: body.success, stillAvailable: body.success, route: toRoutePlan(body.route) };
  },

  async skipOffer(sessionId, offerId) {
    await request(`/app/sessions/${sessionId}/orders/${offerId}/skip`, { method: "POST" });
  },

  async confirmPickup(sessionId, _offerId) {
    const body = await request<any>(`/app/sessions/${sessionId}/pickup`, { method: "POST" });
    return { route: toRoutePlan(body.route)! };
  },

  async confirmDropoff(sessionId, offerId) {
    const body = await request<any>(`/app/sessions/${sessionId}/delivery`, { method: "POST" });
    const meta = sessionMeta.get(sessionId);

    const completed: CompletedDelivery = {
      offerId,
      restaurantName: meta?.activeOfferMeta?.restaurantName ?? "Restaurant",
      grossPay: body.grossPayMxn,
      cost: body.costMxn,
      netEarnings: body.netEarningsMxn,
      minutesUsed: meta?.activeOfferMeta?.additionalTimeMin ?? 0,
      completedAt: new Date().toISOString(),
    };
    const totals: SessionTotals = {
      grossEarnings: body.metrics.grossEarningsMxn,
      netEarnings: body.metrics.netEarningsMxn,
      ordersCompleted: body.metrics.ordersCompleted,
      distanceKm: body.metrics.distanceKm,
      incidentsAvoided: body.metrics.incidentsAvoided,
      startedAt: meta?.startedAt ?? new Date().toISOString(),
    };
    return { completed, totals };
  },

  async getDirectRoute(sessionId) {
    const route = await request<RouteData>(`/app/sessions/${sessionId}/route`);
    return toRoutePlan(route)!;
  },

  async hasTimeForMore(sessionId) {
    const snapshot = await request<any>(`/app/sessions/${sessionId}`);
    const minutesLeft = (new Date(snapshot.deadline).getTime() - Date.now()) / 60000;
    return minutesLeft > snapshot.directRoute.totalDurationMin + 25;
  },

  async tick(sessionId, deltaSeconds): Promise<TickResult> {
    const body = await request<any>(`/app/sessions/${sessionId}/advance`, {
      method: "POST",
      body: JSON.stringify({ elapsedSeconds: deltaSeconds }),
    });
    const events: AppEvent[] = (body.events || []).map((e: any) => ({
      type: e.type,
      message: e.message,
      severity: e.severity,
      createdAt: new Date().toISOString(),
    }));
    return {
      simTimeIso: new Date().toISOString(),
      events,
      arrivedAtPickup: body.arrivedAtPickup,
      arrivedAtDropoff: body.arrivedAtDropoff,
      arrivedAtDestination: body.arrivedAtDestination,
    };
  },

  async getTotals(sessionId) {
    const snapshot = await request<any>(`/app/sessions/${sessionId}`);
    const meta = sessionMeta.get(sessionId);
    return {
      grossEarnings: snapshot.metrics.grossEarningsMxn,
      netEarnings: snapshot.metrics.netEarningsMxn,
      ordersCompleted: snapshot.metrics.ordersCompleted,
      distanceKm: snapshot.metrics.distanceKm,
      incidentsAvoided: snapshot.metrics.incidentsAvoided,
      startedAt: meta?.startedAt ?? snapshot.startTime,
    };
  },
};

export { ApiError };
