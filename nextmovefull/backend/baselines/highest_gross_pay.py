"""
Baseline oficial (results_table_template.csv, columna "HighestPay").

En el flujo oficial /decide se evalúa UN pedido a la vez (no un lote de
ofertas simultáneas), así que "highest gross pay" se traduce en: acepta
cualquier pedido seguro y con ruta viable cuyo pago BRUTO total alcance un
piso fijo (BASELINE_HIGHEST_PAY_MIN_TOTAL_MXN), sin mirar demanda futura,
batching ni ganancia por minuto. Esto preserva el espíritu de la estrategia
original ("de los viables, prioriza pago alto") en un entorno de pings
secuenciales.
"""
from __future__ import annotations

from config.safety_limits import BASELINE_HIGHEST_PAY_MIN_TOTAL_MXN
from decision_engine import build_route_estimate, evaluate_official_constraints
from domain_models import CourierState, Order
from reason_builder import (
    reason_for_baseline_accept,
    reason_for_economic_skip,
    reason_for_no_route,
    reason_for_safety_skip,
    reason_for_unavailable,
)


def decide_highest_pay(order: Order, courier: CourierState, is_order_available: bool, blocked_zones: set[int]):
    if not is_order_available:
        return "SKIP", reason_for_unavailable(), None, []

    route = build_route_estimate(order, courier, blocked_zones)
    if route.blocked:
        return "SKIP", reason_for_no_route(), None, []

    results, failure = evaluate_official_constraints(order, courier, route)
    if failure is not None:
        return "SKIP", reason_for_safety_skip(failure), failure.reason_code, results

    if order.total_pay_mxn < BASELINE_HIGHEST_PAY_MIN_TOTAL_MXN:
        reason = (
            f"Skipped: gross pay {order.total_pay_mxn:.0f} MXN is below the "
            f"{BASELINE_HIGHEST_PAY_MIN_TOTAL_MXN:.0f} MXN floor this policy requires."
        )
        return "SKIP", reason, "reservation_wage", results

    return "ACCEPT", reason_for_baseline_accept("HighestPay"), None, results
