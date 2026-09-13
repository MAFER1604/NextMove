import { CITY_ANCHORS } from "../constants/locations";
import { VEHICLE_PROFILES } from "../constants/config";
import { AcceptResult, AppEvent, DataProvider, TickResult } from "../types/api";
import { CompletedDelivery, OrderOffer } from "../types/order";
import { RoutePlan, RouteSegment } from "../types/route";
import { GeoPoint, SessionConfig, SessionTotals } from "../types/session";
import { makeSegment, haversineKm } from "../utils/routeHelpers";

const RESTAURANT_NAMES = [
  "Tacos El Buen Sazón",
  "Sushi Roll Express",
  "Cafetería Aroma",
  "Burger House",
  "Pollo Feliz",
  "Pizza Nostra",
  "Mariscos La Costa",
  "Panadería San Ángel",
];

let idCounter = 0;
const nextId = (prefix: string) => `${prefix}-${(++idCounter).toString(36)}`;

type Stage = "idle" | "to_pickup" | "at_pickup" | "to_dropoff" | "at_dropoff";

interface MockSession {
  id: string;
  config: SessionConfig;
  simNow: Date;
  deadline: Date;
  currentPos: GeoPoint;
  totals: SessionTotals;
  continuousRidingMin: number;
  offers: Map<string, OrderOffer>;
  offerOrder: string[];
  activeOfferId: string | null;
  stage: Stage;
  activeRoute: RoutePlan | null;
  routeElapsedMin: number;
  lastSearchAt: Date;
}

const sessions = new Map<string, MockSession>();

function vehicleSpeed(v: SessionConfig["vehicle"]) {
  return VEHICLE_PROFILES[v].speedKmh;
}

function pickAnchorNear(point: GeoPoint, exclude?: GeoPoint): GeoPoint {
  const sorted = [...CITY_ANCHORS]
    .map((a) => ({ a, d: haversineKm(point, a) }))
    .sort((x, y) => x.d - y.d);
  const pool = sorted.slice(1, 5); // se salta el más cercano (suele ser el propio origen)
  const choice = pool[Math.floor(Math.random() * pool.length)]?.a || sorted[0].a;
  return { latitude: choice.latitude, longitude: choice.longitude, label: choice.label };
}

function jitterPoint(point: GeoPoint, km: number): GeoPoint {
  const dLat = (Math.random() * 2 - 1) * (km / 111);
  const dLng = (Math.random() * 2 - 1) * (km / (111 * Math.cos((point.latitude * Math.PI) / 180)));
  return { latitude: point.latitude + dLat, longitude: point.longitude + dLng, label: point.label };
}

function buildRoute(session: MockSession, pickup: GeoPoint, dropoff: GeoPoint): RoutePlan {
  const speed = vehicleSpeed(session.config.vehicle);
  const segments: RouteSegment[] = [
    makeSegment("to_pickup", session.currentPos, pickup, speed),
    makeSegment("to_dropoff", pickup, dropoff, speed),
    makeSegment("to_destination", dropoff, session.config.destination, speed),
  ];
  const directSegment = makeSegment("direct", session.currentPos, session.config.destination, speed);
  return { segments, directSegment };
}

function totalRouteMinutes(route: RoutePlan): number {
  return route.segments.reduce((sum, s) => sum + s.durationMin, 0);
}

function isNight(date: Date): boolean {
  const h = date.getHours();
  return h >= 22 || h < 5;
}
function isHeatWindow(date: Date): boolean {
  const h = date.getHours();
  return h >= 12 && h < 16;
}

function feasible(session: MockSession, extraMin: number, extraKm: number, weightKg: number, volumeL: number, etaAtDestination: Date): string | null {
  const vehicle = VEHICLE_PROFILES[session.config.vehicle];
  if (isNight(session.simNow) && extraKm > 3) return "restricted_zone";
  const projectedRiding = session.continuousRidingMin + extraMin * 0.4;
  if (projectedRiding > 240) return "break_needed";
  if (isHeatWindow(session.simNow) && projectedRiding > 90) return "heat_limit";
  if (weightKg > vehicle.capKg || volumeL > vehicle.capL) return "capacity_blocked";

  const deadlineWithMargin =
    session.config.flexibility === "strict"
      ? new Date(session.deadline.getTime() - 10 * 60000)
      : session.config.flexibility === "flexible"
      ? new Date(session.deadline.getTime() + 10 * 60000)
      : session.deadline;
  if (etaAtDestination > deadlineWithMargin) return "arrival_risk";

  return null;
}

function generateOffer(session: MockSession): OrderOffer | null {
  const pickup = jitterPoint(pickAnchorNear(session.currentPos), 0.8);
  const dropoffAnchor = pickAnchorNear(pickup, session.config.destination);
  const dropoff = jitterPoint(dropoffAnchor, 0.9);

  const speed = vehicleSpeed(session.config.vehicle);
  const directDirect = makeSegment("direct", session.currentPos, session.config.destination, speed);
  const toPickup = makeSegment("to_pickup", session.currentPos, pickup, speed);
  const toDropoff = makeSegment("to_dropoff", pickup, dropoff, speed);
  const toDestination = makeSegment("to_destination", dropoff, session.config.destination, speed);

  const candidateMin = toPickup.durationMin + 4 /* recogida */ + toDropoff.durationMin + 3 /* entrega */ + toDestination.durationMin;
  const extraMinutes = Math.max(candidateMin - directDirect.durationMin, 1);
  const extraKm = Math.max(
    toPickup.distanceKm + toDropoff.distanceKm + toDestination.distanceKm - directDirect.distanceKm,
    0
  );

  const grossPay = Math.round(35 + Math.random() * 75);
  const weightKg = +(0.3 + Math.random() * 6).toFixed(1);
  const volumeL = +(1 + Math.random() * 14).toFixed(1);
  const cost = extraKm * VEHICLE_PROFILES[session.config.vehicle].costPerKm;
  const netEarnings = Math.round(grossPay - cost);
  const etaAtDestination = new Date(session.simNow.getTime() + candidateMin * 60000);

  const blockReason = feasible(session, extraMinutes, extraKm, weightKg, volumeL, etaAtDestination);
  if (blockReason && blockReason !== "arrival_risk") return null; // se filtra en silencio, salvo riesgo leve de llegada

  const createdAt = session.simNow.toISOString();
  const expiresAt = new Date(session.simNow.getTime() + 60000).toISOString();

  return {
    id: nextId("offer"),
    restaurantName: RESTAURANT_NAMES[Math.floor(Math.random() * RESTAURANT_NAMES.length)],
    dropoffLabel: dropoffAnchor.label,
    netEarnings,
    grossPay,
    extraMinutes: Math.round(extraMinutes),
    extraKm: +extraKm.toFixed(1),
    etaAtDestination: etaAtDestination.toISOString(),
    reasonShort:
      blockReason === "arrival_risk"
        ? "This order may cut it close, but still fits your flexibility."
        : "This is the most profitable available order that keeps your arrival on time.",
    prepTimeMin: Math.round(6 + Math.random() * 8),
    createdAt,
    expiresAt,
    pickup,
    dropoff,
    status: "available",
    orderNumber: `#${1000 + Math.floor(Math.random() * 8999)}`,
  };
}

function rankOffers(session: MockSession): OrderOffer[] {
  return session.offerOrder
    .map((id) => session.offers.get(id)!)
    .filter((o) => o && o.status === "available")
    .sort((a, b) => b.netEarnings - a.netEarnings);
}

/* --------------------------------------------------------------------- */

export const mockApi: DataProvider = {
  isMock: true,

  async checkConnection() {
    return true;
  },

  async startSession(config) {
    const id = nextId("session");
    const now = new Date();
    let deadline = new Date(config.deadline);
    if (deadline.getTime() < now.getTime()) deadline = new Date(deadline.getTime() + 24 * 3600 * 1000);

    sessions.set(id, {
      id,
      config,
      simNow: now,
      deadline,
      currentPos: config.currentLocation,
      totals: {
        grossEarnings: 0,
        netEarnings: 0,
        ordersCompleted: 0,
        distanceKm: 0,
        incidentsAvoided: 0,
        startedAt: now.toISOString(),
      },
      continuousRidingMin: 0,
      offers: new Map(),
      offerOrder: [],
      activeOfferId: null,
      stage: "idle",
      activeRoute: null,
      routeElapsedMin: 0,
      lastSearchAt: now,
    });
    return { sessionId: id };
  },

  async endSession(sessionId) {
    sessions.delete(sessionId);
  },

  async searchOrders(sessionId) {
    const session = sessions.get(sessionId);
    if (!session) return [];

    // Genera un pequeño lote de candidatos y descarta los no viables.
    const candidates: OrderOffer[] = [];
    let attempts = 0;
    while (candidates.length < 3 && attempts < 12) {
      attempts++;
      const offer = generateOffer(session);
      if (offer) candidates.push(offer);
    }
    for (const offer of candidates) {
      session.offers.set(offer.id, offer);
      session.offerOrder.push(offer.id);
    }
    session.lastSearchAt = session.simNow;
    return rankOffers(session);
  },

  async refreshOffer(sessionId, offerId) {
    const session = sessions.get(sessionId);
    if (!session) return null;
    const offer = session.offers.get(offerId);
    if (!offer) return null;

    if (offer.status === "available") {
      if (new Date(offer.expiresAt) <= session.simNow) {
        offer.status = "expired";
      } else if (Math.random() < 0.04) {
        offer.status = "taken";
      }
    }
    return { ...offer };
  },

  async acceptOffer(sessionId, offerId): Promise<AcceptResult> {
    const session = sessions.get(sessionId);
    if (!session) return { success: false, stillAvailable: false, route: null };
    const offer = session.offers.get(offerId);
    if (!offer) return { success: false, stillAvailable: false, route: null };

    if (offer.status !== "available" || new Date(offer.expiresAt) <= session.simNow) {
      if (offer.status === "available") offer.status = "expired";
      return { success: false, stillAvailable: false, route: null };
    }

    offer.status = "accepted";
    session.activeOfferId = offer.id;
    session.stage = "to_pickup";
    const route = buildRoute(session, offer.pickup, offer.dropoff);
    session.activeRoute = route;
    session.routeElapsedMin = 0;
    return { success: true, stillAvailable: true, route };
  },

  async skipOffer(sessionId, offerId) {
    const session = sessions.get(sessionId);
    if (!session) return;
    const offer = session.offers.get(offerId);
    if (offer && offer.status === "available") offer.status = "skipped";
  },

  async confirmPickup(sessionId, offerId) {
    const session = sessions.get(sessionId);
    if (!session || !session.activeRoute) return { route: { segments: [], directSegment: null } };
    session.stage = "to_dropoff";
    return { route: session.activeRoute };
  },

  async confirmDropoff(sessionId, offerId) {
    const session = sessions.get(sessionId);
    const offer = session?.offers.get(offerId);
    if (!session || !offer) {
      throw new Error("Session or offer not found");
    }

    const cost = offer.extraKm * VEHICLE_PROFILES[session.config.vehicle].costPerKm;
    const net = Math.round(offer.grossPay - cost);

    session.totals.grossEarnings = Math.round(session.totals.grossEarnings + offer.grossPay);
    session.totals.netEarnings = Math.round(session.totals.netEarnings + net);
    session.totals.ordersCompleted += 1;
    session.totals.distanceKm = +(session.totals.distanceKm + offer.extraKm).toFixed(1);
    session.continuousRidingMin += offer.extraMinutes * 0.4;

    session.currentPos = offer.dropoff;
    session.stage = "idle";
    session.activeOfferId = null;
    session.activeRoute = null;
    session.routeElapsedMin = 0;
    offer.status = "accepted"; // se conserva como historial

    const completed: CompletedDelivery = {
      offerId: offer.id,
      restaurantName: offer.restaurantName,
      grossPay: offer.grossPay,
      cost: Math.round(cost),
      netEarnings: net,
      minutesUsed: offer.extraMinutes,
      completedAt: session.simNow.toISOString(),
    };
    return { completed, totals: { ...session.totals } };
  },

  async getDirectRoute(sessionId) {
    const session = sessions.get(sessionId);
    if (!session) return { segments: [], directSegment: null };
    const speed = vehicleSpeed(session.config.vehicle);
    const direct = makeSegment("direct", session.currentPos, session.config.destination, speed);
    return { segments: [{ ...direct, type: "to_destination" }], directSegment: null };
  },

  async hasTimeForMore(sessionId) {
    const session = sessions.get(sessionId);
    if (!session) return false;
    const speed = vehicleSpeed(session.config.vehicle);
    const direct = makeSegment("direct", session.currentPos, session.config.destination, speed);
    const minutesLeft = (session.deadline.getTime() - session.simNow.getTime()) / 60000;
    return minutesLeft > direct.durationMin + 25; // margen para otra entrega completa
  },

  async tick(sessionId, deltaSeconds): Promise<TickResult> {
    const session = sessions.get(sessionId);
    if (!session) {
      return { simTimeIso: new Date().toISOString(), events: [], arrivedAtPickup: false, arrivedAtDropoff: false, arrivedAtDestination: false };
    }

    session.simNow = new Date(session.simNow.getTime() + deltaSeconds * 1000);
    const events: AppEvent[] = [];
    let arrivedAtPickup = false;
    let arrivedAtDropoff = false;
    let arrivedAtDestination = false;

    if (session.activeRoute && (session.stage === "to_pickup" || session.stage === "to_dropoff")) {
      session.routeElapsedMin += deltaSeconds / 60;
      const segs = session.activeRoute.segments;
      const pickupThreshold = segs[0].durationMin;
      const dropoffThreshold = pickupThreshold + segs[1].durationMin;

      if (session.stage === "to_pickup" && session.routeElapsedMin >= pickupThreshold) {
        arrivedAtPickup = true;
      }
      if (session.stage === "to_dropoff" && session.routeElapsedMin >= dropoffThreshold) {
        arrivedAtDropoff = true;
      }

      // Eventos aleatorios ligeros durante el trayecto activo
      if (Math.random() < 0.05) {
        session.routeElapsedMin -= 2; // el cierre resta avance neto (efecto de +tiempo)
        events.push({
          type: "road_closure",
          message: "Route updated",
          detail: "A road closure added a few minutes. You are still on time.",
          severity: "info",
          createdAt: session.simNow.toISOString(),
        });
        session.totals.incidentsAvoided += 1;
      }
      if (session.stage === "to_pickup" && Math.random() < 0.03) {
        events.push({
          type: "restaurant_delay",
          message: "Restaurant delay",
          detail: "Your order will take 15 more minutes. We're recalculating your arrival time.",
          severity: "warning",
          createdAt: session.simNow.toISOString(),
        });
      }
    } else if (session.stage === "idle") {
      const speed = vehicleSpeed(session.config.vehicle);
      const remainingKm = haversineKm(session.currentPos, session.config.destination);
      if (remainingKm < 0.25) {
        arrivedAtDestination = true;
      } else {
        // avanza suavemente hacia el destino mientras no hay pedido activo
        const stepKm = (speed * (deltaSeconds / 3600));
        const frac = Math.min(stepKm / Math.max(remainingKm, 0.01), 1);
        session.currentPos = {
          latitude: session.currentPos.latitude + (session.config.destination.latitude - session.currentPos.latitude) * frac,
          longitude: session.currentPos.longitude + (session.config.destination.longitude - session.currentPos.longitude) * frac,
          label: session.currentPos.label,
        };
      }
    }

    const minutesLeft = (session.deadline.getTime() - session.simNow.getTime()) / 60000;
    if (minutesLeft < 12 && minutesLeft > 0 && Math.random() < 0.15) {
      events.push({
        type: "arrival_risk",
        message: "Arrival risk",
        detail: `You're getting close to your arrival deadline.`,
        severity: "danger",
        createdAt: session.simNow.toISOString(),
      });
    }

    return {
      simTimeIso: session.simNow.toISOString(),
      events,
      arrivedAtPickup,
      arrivedAtDropoff,
      arrivedAtDestination,
    };
  },

  async getTotals(sessionId) {
    const session = sessions.get(sessionId);
    if (!session) {
      return { grossEarnings: 0, netEarnings: 0, ordersCompleted: 0, distanceKm: 0, incidentsAvoided: 0, startedAt: new Date().toISOString() };
    }
    return { ...session.totals };
  },
};

export function getMockSessionSnapshot(sessionId: string) {
  const session = sessions.get(sessionId);
  if (!session) return null;
  return {
    currentPos: session.currentPos,
    simNow: session.simNow.toISOString(),
    stage: session.stage,
    activeOfferId: session.activeOfferId,
  };
}
