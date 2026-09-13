"""
Modelos INTERNOS de dominio de NextMove.

Separados a propósito de `models.py` (contrato oficial): esto permite que el
contrato oficial cambie sin reescribir el motor, y nos permite guardar campos
que NextMove necesita (p. ej. `final_destination_zone`, flexibilidad de
llegada, batching) sin ensuciar la respuesta oficial de /decide.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

Vehicle = Literal["moto", "car", "bike"]
Flexibility = Literal["strict", "balanced", "flexible"]


class AgentState(str, Enum):
    WAITING = "waiting"
    EVALUATING = "evaluating"
    DRIVING_TO_PICKUP = "driving_to_pickup"
    WAITING_AT_PICKUP = "waiting_at_pickup"
    DRIVING_TO_DELIVERY = "driving_to_delivery"
    WAITING_AT_DELIVERY = "waiting_at_delivery"
    RETURNING_TO_DESTINATION = "returning_to_destination"
    COMPLETED = "completed"


class ModelStatus(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"


@dataclass
class ShiftConfig:
    """Configuración de turno. shift_end_time es, en la narrativa de NextMove,
    la hora límite para llegar al destino final (p. ej. clases en el Tec)."""

    seed: int
    shift_hours: float
    vehicle: Vehicle
    start_location_zone: int
    sim_start_time: datetime
    shift_end_time: datetime
    final_destination_zone: int  # campo INTERNO, no forma parte del contrato oficial
    flexibility: Flexibility = "balanced"
    scenario_kind: Literal["fixed_demo", "development_seed", "evaluation_seed"] = "development_seed"


@dataclass
class Order:
    order_id: str
    platform: str
    sim_time: datetime
    decision_deadline: datetime
    zone_pickup: int
    zone_dropoff: int
    zone_pickup_name: str
    zone_dropoff_name: str
    distance_pickup_km: float
    distance_delivery_km: float
    base_pay_mxn: float
    est_tip_mxn: float
    surge_multiplier: float
    restaurant_prep_min: float
    weight_kg: float
    volume_liters: float
    vehicle: Vehicle
    estimated_pickup_min: Optional[float] = None
    estimated_delivery_min: Optional[float] = None

    @property
    def total_pay_mxn(self) -> float:
        return round((self.base_pay_mxn * self.surge_multiplier) + self.est_tip_mxn, 2)


@dataclass
class InFlightOrder:
    order: Order
    picked_up: bool = False
    accepted_sim_time: Optional[datetime] = None


@dataclass
class CourierState:
    """Estado completo de un agente/repartidor durante la simulación."""

    agent_id: str
    strategy_name: str
    config: ShiftConfig
    current_zone: int
    sim_time: datetime
    state: AgentState = AgentState.WAITING
    active_orders: list[InFlightOrder] = field(default_factory=list)
    continuous_riding_min: float = 0.0
    last_break_end_time: Optional[datetime] = None
    gross_earnings_mxn: float = 0.0
    operating_cost_mxn: float = 0.0
    distance_km: float = 0.0
    orders_completed: int = 0
    late_deliveries: int = 0
    incidents_avoided: int = 0
    eta_final_destination: Optional[datetime] = None
    last_decision: Optional[dict] = None
    decision_history: list[dict] = field(default_factory=list)
    model_status: ModelStatus = ModelStatus.AVAILABLE
    safety_violations: int = 0

    @property
    def net_earnings_mxn(self) -> float:
        return round(self.gross_earnings_mxn - self.operating_cost_mxn, 2)


@dataclass
class ConstraintResult:
    """Salida estándar de cada restricción, sea de seguridad u oficial."""

    passed: bool
    constraint_name: str
    observed_value: float | int | str | None
    limit_value: float | int | str | None
    reason_code: Optional[str]  # coincide con binding_constraint si no pasa
    detail: str  # texto corto usado para construir la razón legible


@dataclass
class ScoredAlternative:
    option_label: str
    order_ids: tuple[str, ...]
    net_pay_mxn: float
    additional_time_min: float
    additional_distance_km: float
    future_value_mxn: float
    expected_value_mxn: float
    ranking_score: float
    feasible: bool
    rejected_because: Optional[str] = None
