"""
Modelos OFICIALES del contrato Infosys/Courier.

Estos modelos reflejan exactamente los campos descritos en
`backend/contracts/decision_response_schema.json` y en `order_offered` de
`backend/contracts/event_log_schema.json`. No agregan ni renombran campos
oficiales. Cualquier campo adicional que NextMove necesite internamente vive
en `domain_models.py` y se combina en la capa de adaptación (`decide.py`),
nunca aquí.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Vehicle = Literal["moto", "car", "bike"]
Platform = Literal["rappi", "didi", "uber"]
Decision = Literal["ACCEPT", "SKIP"]
Tier = Literal["tier1", "tier2"]

BindingConstraint = Literal[
    "flagged_zone_night",
    "mandatory_break",
    "heat_rule",
    "shift_end_infeasible",
    "vehicle_capacity",
    "reservation_wage",
]


class CourierStateOverrides(BaseModel):
    """Campos opcionales que los jueces pueden enviar para fijar un estado
    del repartidor antes del ping, tal como describe decision_response_schema.json.
    """

    continuous_riding_min: Optional[float] = None
    shift_elapsed_hours: Optional[float] = None
    last_break_end_time: Optional[str] = None
    shift_end_time: Optional[str] = None
    in_flight_orders: Optional[list[str]] = None


class DecideRequest(BaseModel):
    """Contrato oficial de entrada para POST /decide. Coincide en forma con
    `order_offered` de event_log_schema.json más `courier_state_overrides`.
    """

    order_id: str
    platform: Optional[Platform] = None
    sim_time: str
    zone_pickup: int
    zone_dropoff: int
    distance_pickup_km: float
    distance_delivery_km: float
    base_pay_mxn: float
    surge_multiplier: float
    est_tip_mxn: Optional[float] = None
    restaurant_prep_min: Optional[float] = None
    weight_kg: Optional[float] = None
    volume_liters: Optional[float] = None
    vehicle: Vehicle
    courier_state_overrides: Optional[CourierStateOverrides] = None


class Economics(BaseModel):
    net_pay_mxn: Optional[float] = None
    total_time_min: Optional[float] = None
    raw_rate_mxn_hr: Optional[float] = None
    adjusted_rate_mxn_hr: Optional[float] = None
    reservation_wage_mxn_hr: Optional[float] = None
    deadhead_km: Optional[float] = None


class DecideResponse(BaseModel):
    """Contrato oficial de salida para POST /decide.
    required: order_id, decision, reason, latency_ms (según el schema).
    """

    order_id: str
    decision: Decision
    reason: str = Field(..., description="< 40 palabras, nombra la restricción que decidió")
    latency_ms: float
    binding_constraint: Optional[BindingConstraint] = None
    tier: Optional[Tier] = None
    degraded: Optional[bool] = None
    economics: Optional[Economics] = None


class AlternativeConsidered(BaseModel):
    option: str
    rejected_because: str


class ExplainDecisionResponse(BaseModel):
    """Contrato oficial de salida para GET /decisions/{order_id} (explain_decision)."""

    order_id: str
    decision: Decision
    reason: str
    inputs: dict
    alternatives_considered: list[AlternativeConsidered]
