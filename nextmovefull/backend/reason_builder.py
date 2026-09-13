"""
Construye la razón legible (`reason`) para cada decisión usando plantillas
deterministas. NUNCA se llama a Claude/Ollama para redactar esto en tiempo
real (sección 15 del prompt). Cada plantilla queda bajo 40 palabras y nombra
la restricción que realmente decidió (binding_constraint).
"""
from __future__ import annotations

from domain_models import ConstraintResult

MAX_REASON_WORDS = 40


def _clip_words(text: str) -> str:
    words = text.split()
    if len(words) <= MAX_REASON_WORDS:
        return text
    return " ".join(words[:MAX_REASON_WORDS])


def reason_for_safety_skip(result: ConstraintResult) -> str:
    templates = {
        "flagged_zone_night": "Skipped: dropoff zone is flagged and the estimated arrival falls after the 22:00 night safety curfew.",
        "mandatory_break": "Skipped: accepting this order would exceed 4 continuous riding hours before the mandatory 20-minute break.",
        "heat_rule": "Skipped: accepting this order would exceed the 90-minute continuous riding cap during the 12:00-16:00 heat window.",
        "shift_end_infeasible": f"Skipped: {result.detail}.",
        "vehicle_capacity": f"Skipped: {result.detail} for this vehicle.",
    }
    text = templates.get(result.constraint_name, f"Skipped: {result.detail}.")
    return _clip_words(text)


def reason_for_economic_skip(reservation_wage_hr: float, adjusted_rate_hr: float) -> str:
    text = (
        f"Skipped: adjusted rate of {adjusted_rate_hr:.0f} MXN/hr falls below the "
        f"{reservation_wage_hr:.0f} MXN/hr reservation wage after accounting for detour and cost."
    )
    return _clip_words(text)


def reason_for_no_route() -> str:
    return _clip_words("Skipped: no safe feasible route to the destination is available for this order right now.")


def reason_for_unavailable() -> str:
    return _clip_words("Skipped: the order is no longer available by the time it was evaluated.")


def reason_for_accept(ranking_score: float, additional_time_min: float, net_pay_mxn: float) -> str:
    text = (
        f"Accepted: nets {net_pay_mxn:.0f} MXN for {additional_time_min:.0f} extra minutes, "
        f"the best expected net earnings per detour minute among feasible orders right now."
    )
    return _clip_words(text)


def reason_for_baseline_accept(strategy: str) -> str:
    return _clip_words(f"Accepted: highest technically feasible option under the {strategy} policy.")
