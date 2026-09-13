"""
Restricción de seguridad oficial #3 (evaluation_protocol.md, sección 4):

    "Heat rule: continuous riding capped at 90 minutes during 12:00-16:00"
"""
from __future__ import annotations

from config.safety_limits import (
    HEAT_MAX_CONTINUOUS_RIDING_MIN,
    HEAT_WINDOW_END_HOUR,
    HEAT_WINDOW_START_HOUR,
)
from constraints.base import Constraint, RouteEstimate
from domain_models import ConstraintResult, CourierState, Order


def _in_heat_window(hour: int) -> bool:
    return HEAT_WINDOW_START_HOUR <= hour < HEAT_WINDOW_END_HOUR


class HeatRuleConstraint(Constraint):
    name = "heat_rule"

    def check(self, order: Order, courier: CourierState, route: RouteEstimate) -> ConstraintResult:
        if not _in_heat_window(order.sim_time.hour):
            return ConstraintResult(
                passed=True,
                constraint_name=self.name,
                observed_value=order.sim_time.hour,
                limit_value=f"{HEAT_WINDOW_START_HOUR}:00-{HEAT_WINDOW_END_HOUR}:00",
                reason_code=None,
                detail="outside the heat window, rule does not apply",
            )

        projected_riding_min = courier.continuous_riding_min + route.pickup_min + route.dropoff_min
        passed = projected_riding_min <= HEAT_MAX_CONTINUOUS_RIDING_MIN
        return ConstraintResult(
            passed=passed,
            constraint_name=self.name,
            observed_value=round(projected_riding_min, 1),
            limit_value=HEAT_MAX_CONTINUOUS_RIDING_MIN,
            reason_code=None if passed else self.name,
            detail=(
                f"projected continuous riding {projected_riding_min:.0f} min during "
                f"{HEAT_WINDOW_START_HOUR}:00-{HEAT_WINDOW_END_HOUR}:00 exceeds the "
                f"{HEAT_MAX_CONTINUOUS_RIDING_MIN}-min heat limit"
                if not passed
                else "continuous riding time stays within the heat-window limit"
            ),
        )
