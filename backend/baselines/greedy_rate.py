"""
Baseline oficial (results_table_template.csv, columna "GreedyRate").

Acepta cualquier pedido seguro y con ruta viable cuya tasa INMEDIATA
(ganancia neta / tiempo adicional, sin demanda futura ni batching) alcance
un piso fijo. Es el baseline más parecido a NextMove, pero sin mirar hacia
adelante: sirve para aislar cuánto aporta el término de demanda futura y el
batching de NextMove frente a un agente puramente miope.
"""
from __future__ import annotations

from config.safety_limits import BASELINE_GREEDY_RATE_MIN_MXN_HR
from decision_engine import build_route_estimate, evaluate_official_constraints
from domain_models import CourierState, Order
from reason_builder import (
    reason_for_baseline_accept,
    reason_for_no_route,
    reason_for_safety_skip,
    reason_for_unavailable,
)
from scoring import operating_cost_mxn


def decide_greedy_rate(order: Order, courier: CourierState, is_order_available: bool, blocked_zones: set[int]):
    if not is_order_available:
        return "SKIP", reason_for_unavailable(), None, []

    route = build_route_estimate(order, courier, blocked_zones)
    if route.blocked:
        return "SKIP", reason_for_no_route(), None, []

    results, failure = evaluate_official_constraints(order, courier, route)
    if failure is not None:
        return "SKIP", reason_for_safety_skip(failure), failure.reason_code, results

    cost = operating_cost_mxn(route.total_extra_distance_km, order.vehicle)
    net = order.total_pay_mxn - cost
    rate_hr = (net / (route.total_extra_time_min / 60.0)) if route.total_extra_time_min else 0.0

    if rate_hr < BASELINE_GREEDY_RATE_MIN_MXN_HR:
        reason = (
            f"Skipped: immediate rate {rate_hr:.0f} MXN/hr is below the "
            f"{BASELINE_GREEDY_RATE_MIN_MXN_HR:.0f} MXN/hr floor this policy requires."
        )
        return "SKIP", reason, "reservation_wage", results

    return "ACCEPT", reason_for_baseline_accept("GreedyRate"), None, results
