"""
Restricción de seguridad oficial #5 (evaluation_protocol.md, sección 4):

    "Weight and volume limits per vehicle type"

Los límites por vehículo viven en config/safety_limits.py (y se reflejan en
config/vehicle_profiles.json para el simulador/frontend).
"""
from __future__ import annotations

from config.safety_limits import VEHICLE_CAPACITY_KG, VEHICLE_CAPACITY_LITERS
from constraints.base import Constraint, RouteEstimate
from domain_models import ConstraintResult, CourierState, Order


class VehicleCapacityConstraint(Constraint):
    name = "vehicle_capacity"

    def check(self, order: Order, courier: CourierState, route: RouteEstimate) -> ConstraintResult:
        vehicle = order.vehicle
        max_kg = VEHICLE_CAPACITY_KG[vehicle]
        max_l = VEHICLE_CAPACITY_LITERS[vehicle]

        # Suma el peso/volumen de pedidos activos (en caso de batching) + el candidato.
        active_kg = sum(o.order.weight_kg for o in courier.active_orders)
        active_l = sum(o.order.volume_liters for o in courier.active_orders)

        total_kg = active_kg + order.weight_kg
        total_l = active_l + order.volume_liters

        passed = total_kg <= max_kg and total_l <= max_l
        return ConstraintResult(
            passed=passed,
            constraint_name=self.name,
            observed_value=f"{total_kg:.1f}kg/{total_l:.1f}L",
            limit_value=f"{max_kg:.1f}kg/{max_l:.1f}L ({vehicle})",
            reason_code=None if passed else self.name,
            detail=(
                f"{total_kg:.1f}kg or {total_l:.1f}L exceeds the {vehicle} capacity of "
                f"{max_kg:.1f}kg/{max_l:.1f}L"
                if not passed
                else "within vehicle capacity"
            ),
        )
