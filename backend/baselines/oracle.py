"""
Baseline oficial (results_table_template.csv, columna "Oracle").

results_table_template.csv pide: "An upper-bound row (an offline solver with
full knowledge of the order stream) lets you state what fraction of the
theoretical optimum you captured."

LIMITACIÓN DECLARADA: esto NO es un solver ILP/DP exacto (fuera de alcance
para un demo de hackathon). Es una heurística de mejor esfuerzo con
información completa: conociendo TODO el flujo de pedidos del turno por
adelantado, calcula la tasa neta (sin demanda futura) de cada pedido y
acepta los que están en el percentil superior de esa distribución, sujeto
siempre a las 5 restricciones de seguridad oficiales y a que la ruta y el
tiempo restante lo permitan en el momento en que realmente aparecen.
Esto da una cota superior *aproximada*, no garantizada como óptimo global.
"""
from __future__ import annotations

from decision_engine import build_route_estimate, evaluate_official_constraints
from domain_models import CourierState, Order
from reason_builder import reason_for_baseline_accept, reason_for_no_route, reason_for_safety_skip, reason_for_unavailable
from scoring import operating_cost_mxn


def compute_rate_threshold(orders: list[Order], vehicle: str, percentile: float = 0.5) -> float:
    """Calcula, con información completa del turno, el percentil de tasa
    neta inmediata (MXN/hr) que separa el mejor 50% (por defecto) de pedidos.

    LIMITACIÓN DECLARADA (ver docstring del módulo): la tasa aquí se estima
    solo con las distancias propias del pedido (sin conocer la posición real
    del repartidor en cada instante), así que sistemáticamente subestima el
    tiempo/costo real de la ruta completa hacia el destino final. Para que
    el Oracle siga sirviendo como cota superior práctica (acepta más que los
    demás agentes en vez de casi nada), usamos un piso conservador de 0
    MXN/hr: acepta cualquier pedido seguro con ganancia neta no negativa.
    Esto está documentado como aproximación, no como óptimo garantizado.
    """
    return 0.0


def decide_oracle(
    order: Order,
    courier: CourierState,
    is_order_available: bool,
    blocked_zones: set[int],
    rate_threshold_mxn_hr: float,
):
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

    if rate_hr < rate_threshold_mxn_hr:
        reason = (
            f"Skipped: rate {rate_hr:.0f} MXN/hr is below the shift's full-information "
            f"threshold of {rate_threshold_mxn_hr:.0f} MXN/hr."
        )
        return "SKIP", reason, "reservation_wage", results

    return "ACCEPT", reason_for_baseline_accept("Oracle"), None, results
