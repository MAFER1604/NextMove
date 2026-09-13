"""
Restricción de seguridad oficial #2 (evaluation_protocol.md, sección 4):

    "Mandatory 20-minute break after 4 continuous hours"

Si aceptar este pedido haría que el tiempo de manejo continuo del repartidor
supere el límite sin haber tomado el descanso obligatorio, se rechaza.
"""
from __future__ import annotations

from config.safety_limits import (
    MANDATORY_BREAK_MIN,
    MAX_CONTINUOUS_RIDING_MIN_BEFORE_BREAK,
)
from constraints.base import Constraint, RouteEstimate
from domain_models import ConstraintResult, CourierState, Order


class MandatoryBreakConstraint(Constraint):
    name = "mandatory_break"

    def check(self, order: Order, courier: CourierState, route: RouteEstimate) -> ConstraintResult:
        projected_riding_min = courier.continuous_riding_min + route.pickup_min + route.dropoff_min

        passed = projected_riding_min <= MAX_CONTINUOUS_RIDING_MIN_BEFORE_BREAK
        return ConstraintResult(
            passed=passed,
            constraint_name=self.name,
            observed_value=round(projected_riding_min, 1),
            limit_value=MAX_CONTINUOUS_RIDING_MIN_BEFORE_BREAK,
            reason_code=None if passed else self.name,
            detail=(
                f"projected continuous riding {projected_riding_min:.0f} min would exceed "
                f"the {MAX_CONTINUOUS_RIDING_MIN_BEFORE_BREAK}-min limit before a "
                f"{MANDATORY_BREAK_MIN}-min break"
                if not passed
                else "continuous riding time stays within the mandatory-break limit"
            ),
        )
