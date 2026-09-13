"""
Puntuación económica de NextMove (sección 11 y 12 del prompt).

    operating_cost = additional_distance_km * cost_per_km
    net_earnings   = payment - operating_cost
    future_value   = probability_of_next_order * average_expected_net_earnings
                     (solo si queda tiempo para otro pedido)
    expected_value = net_earnings + future_value
    ranking_score  = expected_value / additional_time_minutes

Sin pesos arbitrarios de tráfico/distancia/alineación: esos factores ya
modifican tiempo, costo y desvío antes de llegar aquí.
"""
from __future__ import annotations

from dataclasses import dataclass

from config.safety_limits import DEFAULT_FUEL_MXN_PER_KM
from demand import DemandModel
from deterministic_utils import round_money, round_time_min, round_distance_km, tie_break_key
from domain_models import Order, ScoredAlternative


_demand_model = DemandModel()


def operating_cost_mxn(additional_distance_km: float, vehicle: str, cost_per_km: float | None = None) -> float:
    rate = cost_per_km if cost_per_km is not None else DEFAULT_FUEL_MXN_PER_KM[vehicle]
    return round_money(additional_distance_km * rate)


def score_alternative(
    label: str,
    order_ids: tuple[str, ...],
    total_pay_mxn: float,
    additional_time_min: float,
    additional_distance_km: float,
    vehicle: str,
    enough_time_for_next_order: bool,
    future_zone: int,
    future_hour: int,
    use_future_value: bool = True,
) -> ScoredAlternative:
    cost = operating_cost_mxn(additional_distance_km, vehicle)
    net = round_money(total_pay_mxn - cost)

    future_value = 0.0
    if use_future_value and enough_time_for_next_order:
        future_value = _demand_model.future_value_mxn(future_zone, future_hour)

    expected_value = round_money(net + future_value)
    denom = max(round_time_min(additional_time_min), 0.01)
    ranking_score = round_money(expected_value / denom)

    return ScoredAlternative(
        option_label=label,
        order_ids=order_ids,
        net_pay_mxn=net,
        additional_time_min=round_time_min(additional_time_min),
        additional_distance_km=round_distance_km(additional_distance_km),
        future_value_mxn=future_value,
        expected_value_mxn=expected_value,
        ranking_score=ranking_score,
        feasible=True,
    )


def rank_alternatives(alternatives: list[ScoredAlternative]) -> list[ScoredAlternative]:
    """Ordena de mejor a peor usando ranking_score y la política central de
    desempates. No depende del orden incidental de dicts/sets."""
    feasible = [a for a in alternatives if a.feasible]
    return sorted(feasible, key=lambda a: (-a.ranking_score, tie_break_key(a)))
