"""
Motor de simulación de turnos NextMove.

Corre varios agentes (baselines + NextMove) sobre EXACTAMENTE el mismo flujo
de pedidos y eventos (misma semilla), para una comparación justa. Simplifica
la física de movimiento (no hay pathfinding real) pero mantiene el estado,
las restricciones de seguridad, la puntuación económica y el registro
completo de decisiones/eventos de forma determinista.

Este motor es lo que alimenta los endpoints /simulation/* (internos del
demo, no parte del contrato oficial) y `outputs/event_logs/*.jsonl`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from baselines.accept_all import decide_accept_all
from baselines.greedy_rate import decide_greedy_rate
from baselines.highest_gross_pay import decide_highest_pay
from baselines.nearest_feasible import decide_nearest_first
from baselines.oracle import compute_rate_threshold, decide_oracle
from config.safety_limits import DEFAULT_RESERVATION_WAGE_MXN_HR
from decision_engine import build_route_estimate, decide_next_move
from deterministic_utils import round_money
from domain_models import AgentState, CourierState, InFlightOrder, ModelStatus, Order, ShiftConfig
from event_logger import EventLogger
from scenario_generator import generate_scenario, zone_name
from scoring import operating_cost_mxn
from strategy_provider import StrategyProvider, strategy_provider_singleton

OUTPUTS_DIR = Path(__file__).parent / "outputs"

AGENT_STRATEGIES = ["NextMove", "HighestPay", "NearestFirst", "GreedyRate", "AcceptAll", "Oracle"]
LIVE_DEMO_STRATEGIES = ["HighestPay", "NextMove"]  # lo que se muestra en pantalla (sección 14)


def _order_from_event(ev: dict) -> Order:
    return Order(
        order_id=ev["order_id"],
        platform=ev.get("platform", "rappi"),
        sim_time=datetime.fromisoformat(ev["sim_time"]),
        decision_deadline=datetime.fromisoformat(ev.get("decision_deadline", ev["sim_time"])),
        zone_pickup=ev["zone_pickup"],
        zone_dropoff=ev["zone_dropoff"],
        zone_pickup_name=ev.get("zone_pickup_name", zone_name(ev["zone_pickup"])),
        zone_dropoff_name=ev.get("zone_dropoff_name", zone_name(ev["zone_dropoff"])),
        distance_pickup_km=ev["distance_pickup_km"],
        distance_delivery_km=ev["distance_delivery_km"],
        base_pay_mxn=ev["base_pay_mxn"],
        est_tip_mxn=ev.get("est_tip_mxn", 0.0),
        surge_multiplier=ev["surge_multiplier"],
        restaurant_prep_min=ev.get("restaurant_prep_min", 0.0),
        weight_kg=ev.get("weight_kg", 0.0),
        volume_liters=ev.get("volume_liters", 0.0),
        vehicle=ev["vehicle"],
    )


@dataclass
class PendingCompletion:
    agent_name: str
    order: Order
    completion_time: datetime
    net_pay: float
    cost: float
    extra_distance_km: float


@dataclass
class SimulationSession:
    session_id: str
    seed: int
    scenario_kind: str
    events: list[dict]
    orders_by_id: dict[str, Order]
    final_destination_zone: int
    sim_clock: datetime
    shift_end_time: datetime
    agents: dict[str, CourierState]
    speed: int = 1
    status: Literal["idle", "running", "paused", "completed"] = "idle"
    processed_event_index: int = 0
    blocked_zones: dict[int, datetime] = field(default_factory=dict)  # zone -> expiry
    pending_completions: list[PendingCompletion] = field(default_factory=list)
    decision_log: list[dict] = field(default_factory=list)  # entries con explain_decision completo
    event_logger: EventLogger | None = None
    oracle_rate_threshold: float = 0.0
    strategy_provider: StrategyProvider = field(default_factory=lambda: strategy_provider_singleton)
    reservation_wage_mxn_hr: float = DEFAULT_RESERVATION_WAGE_MXN_HR


_SESSIONS: dict[str, SimulationSession] = {}


def create_session(
    seed: int,
    shift_hours: float,
    vehicle: str,
    start_location_zone: int,
    final_destination_zone: int,
    scenario_kind: str = "development_seed",
    sim_start_time: datetime | None = None,
) -> SimulationSession:
    sim_start_time = sim_start_time or datetime(2026, 3, 21, 15, 0, 0)
    scenario = generate_scenario(
        seed=seed, shift_hours=shift_hours, vehicle=vehicle,
        start_location_zone=start_location_zone, sim_start_time=sim_start_time,
    )

    orders_by_id: dict[str, Order] = {}
    for ev in scenario.events:
        if ev["event"] == "order_offered":
            orders_by_id[ev["order_id"]] = _order_from_event(ev)

    agents: dict[str, CourierState] = {}
    for name in AGENT_STRATEGIES:
        config = ShiftConfig(
            seed=seed, shift_hours=shift_hours, vehicle=vehicle,
            start_location_zone=start_location_zone, sim_start_time=sim_start_time,
            shift_end_time=scenario.shift_end_time, final_destination_zone=final_destination_zone,
            scenario_kind=scenario_kind,
        )
        agents[name] = CourierState(
            agent_id=name, strategy_name=name, config=config,
            current_zone=start_location_zone, sim_time=sim_start_time,
            state=AgentState.WAITING,
        )

    session_id = str(uuid.uuid4())[:8]
    logger = EventLogger(OUTPUTS_DIR / "event_logs" / f"{session_id}.jsonl")
    for ev in scenario.events:
        logger.log(ev)

    oracle_threshold = compute_rate_threshold(list(orders_by_id.values()), vehicle)

    session = SimulationSession(
        session_id=session_id, seed=seed, scenario_kind=scenario_kind,
        events=scenario.events, orders_by_id=orders_by_id,
        final_destination_zone=final_destination_zone, sim_clock=sim_start_time,
        shift_end_time=scenario.shift_end_time, agents=agents,
        event_logger=logger, oracle_rate_threshold=oracle_threshold,
    )
    _SESSIONS[session_id] = session
    return session


def get_session(session_id: str) -> SimulationSession | None:
    return _SESSIONS.get(session_id)


def _current_blocked_zone_set(session: SimulationSession) -> set[int]:
    return {z for z, expiry in session.blocked_zones.items() if expiry > session.sim_clock}


def _decide_for_agent(session: SimulationSession, agent_name: str, order: Order) -> tuple[str, str, str | None, float | None, float | None]:
    """Devuelve (decision, reason, binding_constraint, net_pay, extra_distance_km)."""
    courier = session.agents[agent_name]
    blocked = _current_blocked_zone_set(session)
    is_available = order.order_id in session.orders_by_id  # siempre True aquí; placeholder para futura expiración

    if agent_name == "NextMove":
        degraded = not session.strategy_provider.is_available
        outcome = decide_next_move(
            order, courier, is_available, blocked,
            reservation_wage_mxn_hr=session.reservation_wage_mxn_hr,
            use_future_value=True,
        )
        courier.model_status = ModelStatus.DEGRADED if degraded else ModelStatus.AVAILABLE
        return outcome.decision, outcome.reason, outcome.binding_constraint, outcome.net_pay_mxn, outcome.additional_distance_km

    if agent_name == "HighestPay":
        d, r, bc, _ = decide_highest_pay(order, courier, is_available, blocked)
    elif agent_name == "NearestFirst":
        d, r, bc, _ = decide_nearest_first(order, courier, is_available, blocked)
    elif agent_name == "GreedyRate":
        d, r, bc, _ = decide_greedy_rate(order, courier, is_available, blocked)
    elif agent_name == "AcceptAll":
        d, r, bc, _ = decide_accept_all(order, courier, is_available, blocked)
    elif agent_name == "Oracle":
        d, r, bc, _ = decide_oracle(order, courier, is_available, blocked, session.oracle_rate_threshold)
    else:
        raise ValueError(f"unknown agent {agent_name}")

    net_pay = None
    extra_distance = None
    if d == "ACCEPT":
        route = build_route_estimate(order, courier, blocked)
        cost = operating_cost_mxn(route.total_extra_distance_km, order.vehicle)
        net_pay = round_money(order.total_pay_mxn - cost)
        extra_distance = route.total_extra_distance_km

    return d, r, bc, net_pay, extra_distance


def _process_order_offered(session: SimulationSession, ev: dict, ev_time: datetime, banners: list[dict]) -> None:
    order = session.orders_by_id[ev["order_id"]]
    for agent_name in AGENT_STRATEGIES:
        decision, reason, binding, net_pay, extra_km = _decide_for_agent(session, agent_name, order)
        courier = session.agents[agent_name]

        decision_event = {
            "event": "decision", "order_id": order.order_id,
            "sim_time": ev_time.isoformat(), "decision": decision,
            "reason": reason, "binding_constraint": binding,
            "latency_ms": 0, "tier": "tier1", "agent": agent_name,
        }
        session.event_logger.log(decision_event)
        session.decision_log.append({
            "order_id": order.order_id, "agent": agent_name, "decision": decision,
            "reason": reason, "binding_constraint": binding, "sim_time": ev_time.isoformat(),
            "inputs": {
                "zone_pickup": order.zone_pickup, "zone_dropoff": order.zone_dropoff,
                "base_pay_mxn": order.base_pay_mxn, "surge_multiplier": order.surge_multiplier,
                "continuous_riding_min": courier.continuous_riding_min,
                "current_zone": courier.current_zone,
            },
            "alternatives_considered": [
                {"option": order.order_id, "rejected_because": reason}
            ] if decision == "SKIP" else [],
        })
        courier.last_decision = session.decision_log[-1]

        if decision == "ACCEPT":
            courier.active_orders.append(InFlightOrder(order=order, picked_up=False, accepted_sim_time=ev_time))
            route = build_route_estimate(order, courier, _current_blocked_zone_set(session))
            completion_time = ev_time + timedelta(minutes=route.total_extra_time_min)
            session.pending_completions.append(PendingCompletion(
                agent_name=agent_name, order=order, completion_time=completion_time,
                net_pay=net_pay or 0.0, cost=(order.total_pay_mxn - (net_pay or 0.0)),
                extra_distance_km=extra_km or 0.0,
            ))
            courier.state = AgentState.DRIVING_TO_PICKUP
            courier.continuous_riding_min += route.pickup_min + route.dropoff_min


def _process_shock(ev: dict, ev_time: datetime, session: SimulationSession, banners: list[dict]) -> None:
    if ev["shock_type"] == "closure":
        expiry = ev_time + timedelta(minutes=ev.get("duration_min", 30))
        session.blocked_zones[ev["zone"]] = expiry
        banners.append({"type": "closure", "sim_time": ev["sim_time"], "detail": ev.get("road", "")})
    elif ev["shock_type"] == "surge":
        banners.append({"type": "surge", "sim_time": ev["sim_time"], "zone": ev.get("zone")})
    elif ev["shock_type"] == "delay":
        banners.append({"type": "delay", "sim_time": ev["sim_time"], "order_id": ev.get("order_id")})
    elif ev["shock_type"] == "rain":
        banners.append({"type": "rain", "sim_time": ev["sim_time"]})


def _complete_order(session: SimulationSession, pc: PendingCompletion) -> None:
    agent = session.agents[pc.agent_name]
    agent.active_orders = [io for io in agent.active_orders if io.order.order_id != pc.order.order_id]
    agent.gross_earnings_mxn = round_money(agent.gross_earnings_mxn + pc.order.total_pay_mxn)
    agent.operating_cost_mxn = round_money(agent.operating_cost_mxn + pc.cost)
    agent.distance_km = round_money(agent.distance_km + pc.extra_distance_km)
    agent.orders_completed += 1
    agent.current_zone = pc.order.zone_dropoff
    agent.state = AgentState.WAITING


def tick(session: SimulationSession, advance_sim_minutes: float) -> dict:
    """Avanza el reloj simulado hasta `new_clock`, procesando eventos y
    finalizaciones de entrega en una única línea de tiempo intercalada
    (siempre el evento pendiente más próximo primero). Esto es intencional:
    procesar "todos los eventos" y luego "todas las finalizaciones" haría
    que el resultado dependiera del tamaño del paso de tick, rompiendo el
    determinismo exigido para el replay (sección 21 del protocolo). Con esta
    intercalación, el resultado final a una hora simulada dada es idéntico
    sin importar en qué incrementos se llame a tick()."""
    new_clock = session.sim_clock + timedelta(minutes=advance_sim_minutes)
    banners: list[dict] = []

    while True:
        next_event_time = None
        if session.processed_event_index < len(session.events):
            next_event_time = datetime.fromisoformat(
                session.events[session.processed_event_index]["sim_time"]
            )

        next_completion_time = min(
            (pc.completion_time for pc in session.pending_completions), default=None
        )

        candidates = [t for t in (next_event_time, next_completion_time) if t is not None and t <= new_clock]
        if not candidates:
            break
        due_time = min(candidates)

        # Desempate determinista cuando coinciden exactamente: primero las
        # finalizaciones de entrega (liberan capacidad/estado) y luego los
        # eventos del stream, en el orden en que aparecen en `session.events`.
        if next_completion_time is not None and next_completion_time == due_time:
            due = [pc for pc in session.pending_completions if pc.completion_time == due_time]
            due.sort(key=lambda pc: (pc.agent_name, pc.order.order_id))
            for pc in due:
                _complete_order(session, pc)
            session.pending_completions = [
                pc for pc in session.pending_completions if pc.completion_time != due_time
            ]
            continue

        ev = session.events[session.processed_event_index]
        ev_time = next_event_time
        session.processed_event_index += 1
        if ev["event"] == "order_offered":
            _process_order_offered(session, ev, ev_time, banners)
        elif ev["event"] == "shock":
            _process_shock(ev, ev_time, session, banners)

    session.sim_clock = new_clock
    if new_clock >= session.shift_end_time and session.status != "completed":
        session.status = "completed"
        for name, agent in session.agents.items():
            agent.state = AgentState.COMPLETED
            session.event_logger.log({
                "event": "shift_end", "sim_time": session.shift_end_time.isoformat(),
                "orders_offered": len(session.orders_by_id), "orders_completed": agent.orders_completed,
                "earnings_mxn": agent.gross_earnings_mxn, "safety_violations": agent.safety_violations,
                "agent": name,
            })
        session.event_logger.flush()

    return {"banners": banners, "sim_time": session.sim_clock.isoformat(), "status": session.status}
