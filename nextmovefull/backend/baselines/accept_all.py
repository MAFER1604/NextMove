"""
Baseline oficial (results_table_template.csv): AcceptAll.

Acepta cualquier pedido que pase las 5 restricciones de seguridad oficiales
y tenga ruta disponible. No usa criterio económico, demanda futura ni
batching. Sirve para medir el "techo" de pedidos completados sin filtro de
rentabilidad, y para demostrar que incluso el baseline más agresivo respeta
la seguridad (safety_violations debe ser 0 para todos los agentes).
"""
from __future__ import annotations

from decision_engine import build_route_estimate, evaluate_official_constraints
from domain_models import CourierState, Order
from reason_builder import reason_for_baseline_accept, reason_for_no_route, reason_for_safety_skip, reason_for_unavailable


def decide_accept_all(order: Order, courier: CourierState, is_order_available: bool, blocked_zones: set[int]):
    if not is_order_available:
        return "SKIP", reason_for_unavailable(), None, []

    route = build_route_estimate(order, courier, blocked_zones)
    if route.blocked:
        return "SKIP", reason_for_no_route(), None, []

    results, failure = evaluate_official_constraints(order, courier, route)
    if failure is not None:
        return "SKIP", reason_for_safety_skip(failure), failure.reason_code, results

    return "ACCEPT", reason_for_baseline_accept("AcceptAll"), None, results
