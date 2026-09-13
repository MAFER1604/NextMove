import { useCallback, useEffect, useRef, useState } from "react";
import { USE_MOCK } from "../constants/config";
import { api } from "../services/api";
import { mockApi } from "../services/mockApi";
import { CompletedDelivery, OrderOffer } from "../types/order";
import { RoutePlan } from "../types/route";
import { AppState, Flexibility, SessionConfig, SessionTotals, Vehicle } from "../types/session";
import { useNotifications } from "./useNotifications";

const provider = USE_MOCK ? mockApi : api;

// 1 segundo real = 2 minutos simulados. Mantiene la sesión ágil sin sentirse
// instantánea ni artificialmente lenta.
const SIM_MINUTES_PER_TICK = 2;
const TICK_MS = 1000;

export type PostResetTarget = "Welcome" | "SessionSetup" | null;

interface Preferences {
  vehicle: Vehicle;
  flexibility: Flexibility;
}

const DEFAULT_PREFERENCES: Preferences = { vehicle: "car", flexibility: "balanced" };

export function useSession() {
  const [appState, setAppState] = useState<AppState>("setup");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [config, setConfig] = useState<SessionConfig | null>(null);
  const [postResetTarget, setPostResetTarget] = useState<PostResetTarget>(null);
  const preferencesRef = useRef<Preferences>(DEFAULT_PREFERENCES);

  const [offers, setOffers] = useState<OrderOffer[]>([]);
  const [offerIndex, setOfferIndex] = useState(0);
  const [noOrdersFound, setNoOrdersFound] = useState(false);

  const [activeOffer, setActiveOffer] = useState<OrderOffer | null>(null);
  const [route, setRoute] = useState<RoutePlan | null>(null);
  const [arrivedAtStop, setArrivedAtStop] = useState(false);
  const [routeElapsedMin, setRouteElapsedMin] = useState(0);

  const [totals, setTotals] = useState<SessionTotals | null>(null);
  const [lastCompleted, setLastCompleted] = useState<CompletedDelivery | null>(null);
  const [simTime, setSimTime] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [arrivedOnTime, setArrivedOnTime] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  const { notifications, notify, dismiss, clearByScope, clearAll } = useNotifications();

  const tickInFlight = useRef(false);
  const sessionIdRef = useRef<string | null>(null);
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  /* -------------------- Conexión -------------------- */
  const checkConnection = useCallback(() => {
    setConnected(null);
    provider
      .checkConnection()
      .then((ok) => setConnected(ok))
      .catch(() => setConnected(false));
  }, []);

  useEffect(() => {
    let mounted = true;
    provider
      .checkConnection()
      .then((ok) => mounted && setConnected(ok))
      .catch(() => mounted && setConnected(false));
    return () => {
      mounted = false;
    };
  }, []);

  /* -------------------- Bucle de tiempo -------------------- */
  const ACTIVE_STATES: AppState[] = [
    "searching", "reviewing_offer", "confirming_order",
    "to_pickup", "waiting_pickup", "to_dropoff",
    "searching_next", "to_destination",
  ];

  useEffect(() => {
    if (!sessionId || !ACTIVE_STATES.includes(appState)) return;
    const interval = setInterval(async () => {
      if (tickInFlight.current) return;
      tickInFlight.current = true;
      try {
        const result = await provider.tick(sessionId, SIM_MINUTES_PER_TICK * 60);
        // Si la sesión cambió (o se reinició) mientras esperábamos la
        // respuesta, la descartamos: nunca debe pisar un estado más nuevo.
        if (sessionIdRef.current !== sessionId) return;

        setSimTime(result.simTimeIso);
        for (const ev of result.events) {
          notify({
            type: ev.severity === "danger" ? "error" : ev.severity === "warning" ? "warning" : "info",
            message: ev.message + (ev.detail ? ` ${ev.detail}` : ""),
            scope: "delivery",
            dismissible: true,
            autoDismissMs: 5000,
          });
        }
        if (appState === "to_pickup" || appState === "to_dropoff") {
          setRouteElapsedMin((m) => m + SIM_MINUTES_PER_TICK);
        }
        if (result.arrivedAtPickup && appState === "to_pickup") {
          setArrivedAtStop(true);
          setAppState("waiting_pickup");
        }
        if (result.arrivedAtDropoff && appState === "to_dropoff") {
          setArrivedAtStop(true);
        }
        if (result.arrivedAtDestination && (appState === "to_destination" || appState === "searching_next" || appState === "searching")) {
          await finalizeSession();
        }
      } catch {
        setConnected(false);
      } finally {
        tickInFlight.current = false;
      }
    }, TICK_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, appState]);

  /* -------------------- Acciones -------------------- */

  const startSetup = useCallback(async (cfg: SessionConfig) => {
    setBusy(true);
    clearByScope("session", "recommendation", "delivery");
    preferencesRef.current = { vehicle: cfg.vehicle, flexibility: cfg.flexibility };
    try {
      const { sessionId: id } = await provider.startSession(cfg);
      setSessionId(id);
      setConfig(cfg);
      setTotals({ grossEarnings: 0, netEarnings: 0, ordersCompleted: 0, distanceKm: 0, incidentsAvoided: 0, startedAt: new Date().toISOString() });
      setAppState("searching");
      await runSearch(id);
    } catch {
      notify({ type: "error", message: "We couldn't start your trip. Please try again.", scope: "session", dismissible: true });
      setAppState("error");
    } finally {
      setBusy(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runSearch = useCallback(async (idOverride?: string) => {
    const id = idOverride || sessionId;
    if (!id) return;
    setBusy(true);
    try {
      const result = await provider.searchOrders(id);
      setOffers(result);
      setOfferIndex(0);
      setNoOrdersFound(result.length === 0);
      setAppState(result.length > 0 ? "reviewing_offer" : "searching");
    } catch {
      notify({ type: "error", message: "We couldn't reach delivery listings right now.", scope: "recommendation", dismissible: true, autoDismissMs: 5000 });
    } finally {
      setBusy(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const goNextOption = useCallback(async () => {
    if (!sessionId) return;
    const nextIdx = Math.min(offerIndex + 1, offers.length - 1);
    if (nextIdx === offerIndex) {
      await runSearch();
      return;
    }
    const refreshed = await provider.refreshOffer(sessionId, offers[nextIdx].id);
    if (refreshed) {
      setOffers((prev) => prev.map((o, i) => (i === nextIdx ? refreshed : o)));
    }
    setOfferIndex(nextIdx);
  }, [sessionId, offerIndex, offers, runSearch]);

  const goPreviousOption = useCallback(async () => {
    if (!sessionId || offerIndex === 0) return;
    const prevIdx = offerIndex - 1;
    const refreshed = await provider.refreshOffer(sessionId, offers[prevIdx].id);
    if (refreshed) {
      setOffers((prev) => prev.map((o, i) => (i === prevIdx ? refreshed : o)));
    }
    setOfferIndex(prevIdx);
  }, [sessionId, offerIndex, offers]);

  const skipCurrent = useCallback(async () => {
    if (!sessionId || !offers[offerIndex]) return;
    await provider.skipOffer(sessionId, offers[offerIndex].id);
    clearByScope("recommendation");
    if (offerIndex + 1 < offers.length) {
      await goNextOption();
    } else {
      await runSearch();
    }
  }, [sessionId, offers, offerIndex, goNextOption, runSearch, clearByScope]);

  const acceptCurrent = useCallback(async () => {
    if (!sessionId || !offers[offerIndex]) return;
    setAppState("confirming_order");
    setBusy(true);
    try {
      const offer = offers[offerIndex];
      const result = await provider.acceptOffer(sessionId, offer.id);
      if (!result.success || !result.stillAvailable || !result.route) {
        notify({
          type: "error",
          message: "This order is no longer available. Here's your next best option.",
          scope: "recommendation", dismissible: true, autoDismissMs: 4500,
        });
        setOffers((prev) => prev.map((o) => (o.id === offer.id ? { ...o, status: "expired" } : o)));
        await runSearch();
        return;
      }
      clearByScope("recommendation");
      setActiveOffer(offer);
      setRoute(result.route);
      setRouteElapsedMin(0);
      setArrivedAtStop(false);
      setAppState("to_pickup");
    } catch {
      notify({ type: "error", message: "We couldn't confirm this order. Please try again.", scope: "recommendation", dismissible: true, autoDismissMs: 4500 });
      setAppState("reviewing_offer");
    } finally {
      setBusy(false);
    }
  }, [sessionId, offers, offerIndex, runSearch, clearByScope]);

  const confirmPickup = useCallback(async () => {
    if (!sessionId || !activeOffer) return;
    setBusy(true);
    try {
      const result = await provider.confirmPickup(sessionId, activeOffer.id);
      setRoute(result.route);
      setArrivedAtStop(false);
      setAppState("to_dropoff");
    } catch {
      notify({ type: "error", message: "We couldn't confirm the pickup. Please try again.", scope: "delivery", dismissible: true, autoDismissMs: 4500 });
    } finally {
      setBusy(false);
    }
  }, [sessionId, activeOffer]);

  const confirmDropoff = useCallback(async () => {
    if (!sessionId || !activeOffer) return;
    setBusy(true);
    try {
      const result = await provider.confirmDropoff(sessionId, activeOffer.id);
      setLastCompleted(result.completed);
      setTotals(result.totals);
      setActiveOffer(null);
      setRoute(null);
      setArrivedAtStop(false);
      clearByScope("delivery");
      setAppState("delivery_completed");
    } catch {
      notify({ type: "error", message: "We couldn't confirm the delivery. Please try again.", scope: "delivery", dismissible: true, autoDismissMs: 4500 });
    } finally {
      setBusy(false);
    }
  }, [sessionId, activeOffer, clearByScope]);

  const findNextOrder = useCallback(async () => {
    if (!sessionId) return;
    const canContinue = await provider.hasTimeForMore(sessionId);
    if (!canContinue) {
      await headToDestination();
      return;
    }
    setAppState("searching_next");
    await runSearch();
  }, [sessionId, runSearch]);

  const headToDestination = useCallback(async () => {
    if (!sessionId) return;
    setBusy(true);
    try {
      const directRoute = await provider.getDirectRoute(sessionId);
      setRoute(directRoute);
      setAppState("to_destination");
    } finally {
      setBusy(false);
    }
  }, [sessionId]);

  const finalizeSession = useCallback(async () => {
    if (!config) return;
    const now = simTime ? new Date(simTime) : new Date();
    const deadline = new Date(config.deadline);
    const margin = config.flexibility === "flexible" ? 10 : config.flexibility === "strict" ? -10 : 0;
    const onTime = now.getTime() <= deadline.getTime() + margin * 60000;
    setArrivedOnTime(onTime);
    // Regla explícita del brief: al entrar a SessionSummary se eliminan
    // todas las notificaciones con scope recommendation, delivery o session.
    clearByScope("recommendation", "delivery", "session");
    setAppState("session_completed");
  }, [config, simTime, clearByScope]);

  /**
   * Función central única de limpieza (sección 18 del brief). Cancela todo
   * lo pendiente, borra la sesión del lado del backend, resetea el estado
   * de React y decide a dónde navegar después.
   */
  const resetSession = useCallback(
    async (options: { preservePreferences: boolean }) => {
      const idToClose = sessionIdRef.current;
      // 1. Invalida cualquier tick en vuelo y evita que el bucle de tiempo
      //    vuelva a programarse: se hace poniendo sessionId a null primero.
      setSessionId(null);
      sessionIdRef.current = null;

      // 2. Termina/borra la sesión anterior en el backend (best-effort: si
      //    falla, igual continuamos limpiando el lado del cliente).
      if (idToClose) {
        try {
          await provider.endSession(idToClose);
        } catch {
          // no bloquea el reset si el backend no responde
        }
      }

      // 3. Limpia todo el estado de React.
      setConfig(null);
      setOffers([]);
      setOfferIndex(0);
      setNoOrdersFound(false);
      setActiveOffer(null);
      setRoute(null);
      setArrivedAtStop(false);
      setRouteElapsedMin(0);
      setTotals(null);
      setLastCompleted(null);
      setSimTime(null);
      setArrivedOnTime(null);
      setBusy(false);
      clearAll();

      // 4. Preferencias: se conservan solo para "Start another trip".
      if (!options.preservePreferences) {
        preferencesRef.current = DEFAULT_PREFERENCES;
      }

      setAppState("setup");
      setPostResetTarget(options.preservePreferences ? "SessionSetup" : "Welcome");
    },
    [clearAll]
  );

  const consumePostResetTarget = useCallback(() => setPostResetTarget(null), []);

  return {
    appState, sessionId, config, busy, postResetTarget,
    preferences: preferencesRef.current,
    offers, offerIndex, currentOffer: offers[offerIndex] ?? null, noOrdersFound,
    activeOffer, route, arrivedAtStop, routeElapsedMin,
    totals, lastCompleted, notifications, simTime, connected, arrivedOnTime,
    isMock: provider.isMock,
    actions: {
      startSetup, runSearch, goNextOption, goPreviousOption, skipCurrent, acceptCurrent,
      confirmPickup, confirmDropoff, findNextOrder, headToDestination,
      startAnotherTrip: () => resetSession({ preservePreferences: true }),
      returnHome: () => resetSession({ preservePreferences: false }),
      dismissNotification: dismiss,
      consumePostResetTarget,
      retryConnection: checkConnection,
    },
  };
}

export type UseSessionReturn = ReturnType<typeof useSession>;
