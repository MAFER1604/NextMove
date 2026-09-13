"""
Interfaz base para las restricciones de NextMove.

Cada restricción es una función pura: (order, courier_state, route_estimate,
config) -> ConstraintResult. No dependen de I/O, red, ni del modelo de
lenguaje. Esto es lo que permite que el fast path de /decide se mantenga
dentro del presupuesto de 50 ms y sea 100% determinista.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain_models import ConstraintResult, CourierState, Order


@dataclass
class RouteEstimate:
    """Estimación de tiempos/distancias para evaluar un pedido candidato,
    calculada por routing.py antes de llegar a las restricciones."""

    pickup_min: float
    dropoff_min: float
    total_extra_time_min: float  # tiempo adicional sobre la ruta directa
    total_extra_distance_km: float
    arrival_at_final_destination: datetime
    blocked: bool = False  # True si no existe ruta segura (p.ej. cierre vial total)
    block_reason: str = ""


class Constraint:
    name: str = "base"

    def check(
        self,
        order: Order,
        courier: CourierState,
        route: RouteEstimate,
    ) -> ConstraintResult:
        raise NotImplementedError
