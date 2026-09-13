"""
Baseline oficial (results_table_template.csv, columna "NearestFirst").

Acepta cualquier pedido seguro y con ruta viable cuya distancia de recogida
(deadhead) sea menor o igual a un umbral fijo. No considera pago, demanda
futura ni batching: prioriza minimizar el desvío inmediato.
"""
from __future__ import annotations

from config.safety_limits import BASELINE_NEAREST_MAX_PICKUP_KM
from decision_engine import build_route_estimate, evaluate_official_constraints
from domain_models import CourierState, Order
from reason_builder import (
    reason_for_baseline_accept,
    reason_for_no_route,
    reason_for_safety_skip,
    reason_for_unavailable,
)


def decide_nearest_first(order: Order, courier: CourierState, is_order_available: bool, blocked_zones: set[int]):
    if not is_order_available:
        return "SKIP", reason_for_unavailable(), None, []

    route = build_route_estimate(order, courier, blocked_zones)
    if route.blocked:
        return "SKIP", reason_for_no_route(), None, []

    results, failure = evaluate_official_constraints(order, courier, route)
    if failure is not None:
        return "SKIP", reason_for_safety_skip(failure), failure.reason_code, results

    if order.distance_pickup_km > BASELINE_NEAREST_MAX_PICKUP_KM:
        reason = (
            f"Skipped: pickup distance {order.distance_pickup_km:.1f} km exceeds the "
            f"{BASELINE_NEAREST_MAX_PICKUP_KM:.1f} km limit this policy accepts."
        )
        return "SKIP", reason, "reservation_wage", results

    return "ACCEPT", reason_for_baseline_accept("NearestFirst"), None, results
