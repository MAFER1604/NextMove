"""
Restricción de seguridad oficial #1 (evaluation_protocol.md, sección 4):

    "No dropoff in flagged zones after 22:00"

Límite exacto y lista de zonas viven en config/safety_limits.py, no aquí.
"""
from __future__ import annotations

from config.safety_limits import FLAGGED_ZONES_NIGHT, NIGHT_CURFEW_HOUR
from constraints.base import Constraint, RouteEstimate
from domain_models import ConstraintResult, CourierState, Order


class FlaggedZoneNightConstraint(Constraint):
    name = "flagged_zone_night"

    def check(self, order: Order, courier: CourierState, route: RouteEstimate) -> ConstraintResult:
        # El momento relevante es cuando el repartidor llegaría a hacer el dropoff:
        # sim_time del pedido + tiempo de recogida + tiempo de tránsito/entrega.
        from datetime import timedelta

        eta_dropoff = order.sim_time + timedelta(minutes=route.pickup_min + route.dropoff_min)
        is_night = eta_dropoff.hour >= NIGHT_CURFEW_HOUR or eta_dropoff.hour < 5
        in_flagged_zone = order.zone_dropoff in FLAGGED_ZONES_NIGHT

        passed = not (is_night and in_flagged_zone)
        return ConstraintResult(
            passed=passed,
            constraint_name=self.name,
            observed_value=f"zone={order.zone_dropoff}@{eta_dropoff.strftime('%H:%M')}",
            limit_value=f"flagged_zones={sorted(FLAGGED_ZONES_NIGHT)} after {NIGHT_CURFEW_HOUR}:00",
            reason_code=None if passed else self.name,
            detail=(
                f"dropoff zone {order.zone_dropoff} is flagged and ETA "
                f"{eta_dropoff.strftime('%H:%M')} is after {NIGHT_CURFEW_HOUR}:00"
                if not passed
                else "dropoff zone/time is within the night safety window"
            ),
        )
