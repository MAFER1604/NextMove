"""
Motor central de decisión de NextMove.

Orden de validación (sección 8 del prompt):
  1. Estructura y estado (order todavía disponible)   -> availability
  2. Restricciones oficiales de seguridad              -> constraints/__init__.py
  3. Disponibilidad (repetido por claridad, no-op aquí)
  4. Ruta existente (bloqueo por cierre vial / incidente)
  5. Tiempo de llegada (cubierto por shift_end_infeasible + margen de ruta)
  6. Viabilidad económica (reservation_wage)
  7. Puntuación de alternativas viables (scoring.py)

Devuelve una estructura interna rica; `decide.py` la adapta al contrato
oficial `DecideResponse`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from config.safety_limits import DEFAULT_RESERVATION_WAGE_MXN_HR
from constraints import OFFICIAL_SAFETY_CONSTRAINTS
from constraints.base import RouteEstimate
from domain_models import ConstraintResult, CourierState, Order
from reason_builder import (
    reason_for_accept,
    reason_for_economic_skip,
    reason_for_no_route,
    reason_for_safety_skip,
    reason_for_unavailable,
)
from routing import MockRouteProvider
from scoring import score_alternative

_route_provider = MockRouteProvider()


@dataclass
class DecisionOutcome:
    decision: str  # "ACCEPT" | "SKIP"
    reason: str
    binding_constraint: str | None
    tier: str
    net_pay_mxn: float | None
    additional_time_min: float | None
    additional_distance_km: float | None
    adjusted_rate_mxn_hr: float | None
    raw_rate_mxn_hr: float | None
    deadhead_km: float | None
    constraints_evaluated: list[ConstraintResult]
    alternatives_considered: list[dict]


def build_route_estimate(order: Order, courier: CourierState, blocked_zones: set[int]) -> RouteEstimate:
    from config.safety_limits import BASE_DROPOFF_MIN, BASE_PICKUP_MIN

    pickup_extra = BASE_PICKUP_MIN
    dropoff_extra = BASE_DROPOFF_MIN + order.restaurant_prep_min
    traffic_multiplier = 1.0

    return _route_provider.estimate_candidate(
        current_zone=courier.current_zone,
        pickup_zone=order.zone_pickup,
        dropoff_zone=order.zone_dropoff,
        final_destination_zone=courier.config.final_destination_zone,
        vehicle=order.vehicle,
        pickup_extra_min=pickup_extra,
        dropoff_extra_min=dropoff_extra,
        restaurant_delay_min=0.0,
        traffic_multiplier=traffic_multiplier,
        blocked_zones=blocked_zones,
        sim_time=order.sim_time,
    )


def evaluate_official_constraints(
    order: Order, courier: CourierState, route: RouteEstimate
) -> tuple[list[ConstraintResult], ConstraintResult | None]:
    """Corre las 5 restricciones oficiales en orden. Devuelve la lista completa
    (para explain_decision) y la PRIMERA que falle (binding constraint), o
    None si todas pasan."""
    results: list[ConstraintResult] = []
    first_failure: ConstraintResult | None = None
    for constraint in OFFICIAL_SAFETY_CONSTRAINTS:
        result = constraint.check(order, courier, route)
        results.append(result)
        if not result.passed and first_failure is None:
            first_failure = result
    return results, first_failure


def decide_next_move(
    order: Order,
    courier: CourierState,
    is_order_available: bool,
    blocked_zones: set[int],
    reservation_wage_mxn_hr: float = DEFAULT_RESERVATION_WAGE_MXN_HR,
    use_future_value: bool = True,
) -> DecisionOutcome:
    """Estrategia NextMove: seguridad -> disponibilidad -> ruta -> tiempo ->
    economía -> puntuación."""

    # 1. Disponibilidad
    if not is_order_available:
        return DecisionOutcome(
            decision="SKIP", reason=reason_for_unavailable(), binding_constraint=None,
            tier="tier1", net_pay_mxn=None, additional_time_min=None,
            additional_distance_km=None, adjusted_rate_mxn_hr=None, raw_rate_mxn_hr=None,
            deadhead_km=None, constraints_evaluated=[], alternatives_considered=[],
        )

    route = build_route_estimate(order, courier, blocked_zones)

    # 4. Ruta existente
    if route.blocked:
        return DecisionOutcome(
            decision="SKIP", reason=reason_for_no_route(), binding_constraint=None,
            tier="tier1", net_pay_mxn=None, additional_time_min=None,
            additional_distance_km=None, adjusted_rate_mxn_hr=None, raw_rate_mxn_hr=None,
            deadhead_km=None, constraints_evaluated=[], alternatives_considered=[
                {"option": order.order_id, "rejected_because": route.block_reason}
            ],
        )

    # 2/5. Restricciones oficiales de seguridad (incluye shift_end_infeasible = tiempo de llegada)
    results, failure = evaluate_official_constraints(order, courier, route)
    if failure is not None:
        return DecisionOutcome(
            decision="SKIP", reason=reason_for_safety_skip(failure),
            binding_constraint=failure.reason_code, tier="tier1",
            net_pay_mxn=None, additional_time_min=route.total_extra_time_min,
            additional_distance_km=route.total_extra_distance_km,
            adjusted_rate_mxn_hr=None, raw_rate_mxn_hr=None, deadhead_km=order.distance_pickup_km,
            constraints_evaluated=results,
            alternatives_considered=[{"option": order.order_id, "rejected_because": failure.detail}],
        )

    # 6/7. Viabilidad económica y puntuación
    alt = score_alternative(
        label=order.order_id,
        order_ids=(order.order_id,),
        total_pay_mxn=order.total_pay_mxn,
        additional_time_min=route.total_extra_time_min,
        additional_distance_km=route.total_extra_distance_km,
        vehicle=order.vehicle,
        enough_time_for_next_order=_has_time_for_another(order, courier, route),
        future_zone=order.zone_dropoff,
        future_hour=order.sim_time.hour,
        use_future_value=use_future_value,
    )

    raw_rate_hr = round(order.total_pay_mxn / (route.total_extra_time_min / 60.0), 2) if route.total_extra_time_min else 0.0
    adjusted_rate_hr = round(alt.expected_value_mxn / (route.total_extra_time_min / 60.0), 2) if route.total_extra_time_min else 0.0

    if adjusted_rate_hr < reservation_wage_mxn_hr:
        return DecisionOutcome(
            decision="SKIP",
            reason=reason_for_economic_skip(reservation_wage_mxn_hr, adjusted_rate_hr),
            binding_constraint="reservation_wage", tier="tier1",
            net_pay_mxn=alt.net_pay_mxn, additional_time_min=route.total_extra_time_min,
            additional_distance_km=route.total_extra_distance_km,
            adjusted_rate_mxn_hr=adjusted_rate_hr, raw_rate_mxn_hr=raw_rate_hr,
            deadhead_km=order.distance_pickup_km, constraints_evaluated=results,
            alternatives_considered=[{
                "option": order.order_id,
                "rejected_because": f"adjusted rate {adjusted_rate_hr:.0f} MXN/hr below reservation wage {reservation_wage_mxn_hr:.0f} MXN/hr",
            }],
        )

    return DecisionOutcome(
        decision="ACCEPT",
        reason=reason_for_accept(alt.ranking_score, route.total_extra_time_min, alt.net_pay_mxn),
        binding_constraint=None, tier="tier1",
        net_pay_mxn=alt.net_pay_mxn, additional_time_min=route.total_extra_time_min,
        additional_distance_km=route.total_extra_distance_km,
        adjusted_rate_mxn_hr=adjusted_rate_hr, raw_rate_mxn_hr=raw_rate_hr,
        deadhead_km=order.distance_pickup_km, constraints_evaluated=results,
        alternatives_considered=[],
    )


def _has_time_for_another(order: Order, courier: CourierState, route: RouteEstimate) -> bool:
    remaining_min = (courier.config.shift_end_time - route.arrival_at_final_destination).total_seconds() / 60.0
    # Umbral simple y explícito: se necesita al menos el tiempo base de otro
    # pickup+dropoff para que valga la pena contar el valor futuro.
    from config.safety_limits import BASE_DROPOFF_MIN, BASE_PICKUP_MIN

    return remaining_min >= (BASE_PICKUP_MIN + BASE_DROPOFF_MIN) * 2
