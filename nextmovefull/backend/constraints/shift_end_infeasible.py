"""
Restricción de seguridad oficial #4 (evaluation_protocol.md, sección 4):

    "Refuse orders that cannot be completed before shift end"

En la narrativa de NextMove, `shift_end_time` es la hora límite para llegar
al destino final del usuario (p. ej. llegar a clases). Esta restricción
verifica que, tras completar el pedido, el repartidor todavía pueda llegar
a `final_destination_zone` antes de esa hora.
"""
from __future__ import annotations

from constraints.base import Constraint, RouteEstimate
from domain_models import ConstraintResult, CourierState, Order


class ShiftEndInfeasibleConstraint(Constraint):
    name = "shift_end_infeasible"

    def check(self, order: Order, courier: CourierState, route: RouteEstimate) -> ConstraintResult:
        deadline = courier.config.shift_end_time
        eta = route.arrival_at_final_destination
        passed = eta <= deadline

        minutes_over = max((eta - deadline).total_seconds() / 60.0, 0.0)
        return ConstraintResult(
            passed=passed,
            constraint_name=self.name,
            observed_value=eta.isoformat(),
            limit_value=deadline.isoformat(),
            reason_code=None if passed else self.name,
            detail=(
                f"completing this order would arrive {minutes_over:.0f} minutes after "
                f"the {deadline.strftime('%H:%M')} deadline"
                if not passed
                else "arrival at the final destination stays within the deadline"
            ),
        )
