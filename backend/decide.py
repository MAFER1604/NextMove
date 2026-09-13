"""
Adaptador del endpoint oficial POST /decide.

Convierte `models.DecideRequest` (contrato oficial) en los modelos internos
de dominio, corre el pipeline de restricciones + puntuación, y adapta el
resultado de vuelta a `models.DecideResponse` (contrato oficial),
respetando el presupuesto de 50 ms.

Esta ruta es completamente autocontenida: si se llama sin una simulación
corriendo (como hace `validate_format.py --endpoint`), construye un estado
de repartidor efímero solo a partir de los campos del request y de
`courier_state_overrides`, con valores por defecto explícitos y visibles.
No hay llamadas a red, disco costoso, Claude, Ollama o TomTom en esta
función.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

from config.safety_limits import (
    BASE_DROPOFF_MIN,
    BASE_PICKUP_MIN,
    DEFAULT_RESERVATION_WAGE_MXN_HR,
)
from constraints import OFFICIAL_SAFETY_CONSTRAINTS
from constraints.base import RouteEstimate
from domain_models import AgentState, CourierState, InFlightOrder, ModelStatus, Order, ShiftConfig
from models import DecideRequest, DecideResponse, Economics
from reason_builder import reason_for_accept, reason_for_economic_skip, reason_for_safety_skip
from scoring import operating_cost_mxn

_VEHICLE_SPEED_KMH = {"bike": 14, "moto": 32, "car": 28}
_DEFAULT_SHIFT_HOURS = 8.0


def _parse_dt(value: str | None, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return fallback


def _order_from_request(req: DecideRequest, sim_time: datetime) -> Order:
    return Order(
        order_id=req.order_id,
        platform=req.platform or "rappi",
        sim_time=sim_time,
        decision_deadline=sim_time + timedelta(seconds=5),
        zone_pickup=req.zone_pickup,
        zone_dropoff=req.zone_dropoff,
        zone_pickup_name=f"Zone {req.zone_pickup}",
        zone_dropoff_name=f"Zone {req.zone_dropoff}",
        distance_pickup_km=req.distance_pickup_km,
        distance_delivery_km=req.distance_delivery_km,
        base_pay_mxn=req.base_pay_mxn,
        est_tip_mxn=req.est_tip_mxn or 0.0,
        surge_multiplier=req.surge_multiplier,
        restaurant_prep_min=req.restaurant_prep_min or 0.0,
        weight_kg=req.weight_kg or 0.0,
        volume_liters=req.volume_liters or 0.0,
        vehicle=req.vehicle,
    )


def _ephemeral_courier(req: DecideRequest, order: Order) -> CourierState:
    overrides = req.courier_state_overrides
    continuous_riding_min = (overrides.continuous_riding_min if overrides else None) or 0.0
    shift_elapsed_hours = (overrides.shift_elapsed_hours if overrides else None) or 0.0
    shift_end_time = _parse_dt(
        overrides.shift_end_time if overrides else None,
        fallback=order.sim_time + timedelta(hours=_DEFAULT_SHIFT_HOURS - shift_elapsed_hours),
    )

    config = ShiftConfig(
        seed=0,
        shift_hours=_DEFAULT_SHIFT_HOURS,
        vehicle=order.vehicle,
        start_location_zone=order.zone_pickup,
        sim_start_time=order.sim_time - timedelta(hours=shift_elapsed_hours),
        shift_end_time=shift_end_time,
        final_destination_zone=order.zone_dropoff,
        scenario_kind="development_seed",
    )

    return CourierState(
        agent_id="decide-endpoint-probe",
        strategy_name="NextMove",
        config=config,
        current_zone=order.zone_pickup,
        sim_time=order.sim_time,
        state=AgentState.EVALUATING,
        continuous_riding_min=continuous_riding_min,
        model_status=ModelStatus.AVAILABLE,
    )


def _route_from_given_distances(order: Order) -> RouteEstimate:
    """Para el endpoint standalone usamos las distancias YA PROVISTAS en el
    request oficial (distance_pickup_km, distance_delivery_km) en vez de
    recalcularlas por zona: son datos reales del contrato, no hay que
    inventarlos. La "llegada al destino final" se interpreta aquí como el
    momento en que se completa la entrega (ver limitación en README: el
    contrato oficial no expone un `final_destination_zone` separado)."""
    speed = _VEHICLE_SPEED_KMH[order.vehicle]
    pickup_extra = BASE_PICKUP_MIN
    dropoff_extra = BASE_DROPOFF_MIN + order.restaurant_prep_min
    transit_min = (order.distance_pickup_km + order.distance_delivery_km) / speed * 60.0
    total_time = pickup_extra + dropoff_extra + transit_min
    arrival = order.sim_time + timedelta(minutes=total_time)

    return RouteEstimate(
        pickup_min=pickup_extra,
        dropoff_min=dropoff_extra,
        total_extra_time_min=max(total_time, 1.0),
        total_extra_distance_km=order.distance_pickup_km + order.distance_delivery_km,
        arrival_at_final_destination=arrival,
        blocked=False,
    )


def handle_decide(req: DecideRequest) -> DecideResponse:
    """Fast path. Presupuesto: 50 ms. Sin red, sin disco costoso, sin
    Claude/Ollama/TomTom. Determinista: misma entrada -> misma salida."""
    t0 = time.perf_counter()

    sim_time = _parse_dt(req.sim_time, fallback=datetime(2026, 1, 1))
    order = _order_from_request(req, sim_time)
    courier = _ephemeral_courier(req, order)
    route = _route_from_given_distances(order)

    binding_constraint = None
    decision = "ACCEPT"
    reason = ""
    net_pay = None
    adjusted_rate_hr = None
    raw_rate_hr = None

    for constraint in OFFICIAL_SAFETY_CONSTRAINTS:
        result = constraint.check(order, courier, route)
        if not result.passed:
            decision = "SKIP"
            reason = reason_for_safety_skip(result)
            binding_constraint = result.reason_code
            break

    if decision == "ACCEPT":
        cost = operating_cost_mxn(route.total_extra_distance_km, order.vehicle)
        net_pay = round(order.total_pay_mxn - cost, 2)
        raw_rate_hr = round(order.total_pay_mxn / (route.total_extra_time_min / 60.0), 2)
        adjusted_rate_hr = round(net_pay / (route.total_extra_time_min / 60.0), 2)

        if adjusted_rate_hr < DEFAULT_RESERVATION_WAGE_MXN_HR:
            decision = "SKIP"
            reason = reason_for_economic_skip(DEFAULT_RESERVATION_WAGE_MXN_HR, adjusted_rate_hr)
            binding_constraint = "reservation_wage"
        else:
            reason = reason_for_accept(0.0, route.total_extra_time_min, net_pay)

    degraded = False  # el endpoint standalone nunca depende del modelo; ver strategy_provider.py

    latency_ms = round((time.perf_counter() - t0) * 1000, 3)

    return DecideResponse(
        order_id=order.order_id,
        decision=decision,
        reason=reason,
        latency_ms=latency_ms,
        binding_constraint=binding_constraint,
        tier="tier1",
        degraded=degraded,
        economics=Economics(
            net_pay_mxn=net_pay,
            total_time_min=route.total_extra_time_min,
            raw_rate_mxn_hr=raw_rate_hr,
            adjusted_rate_mxn_hr=adjusted_rate_hr,
            reservation_wage_mxn_hr=DEFAULT_RESERVATION_WAGE_MXN_HR,
            deadhead_km=order.distance_pickup_km,
        ),
    )
