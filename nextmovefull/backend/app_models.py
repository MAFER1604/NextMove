"""
Modelos del subsistema /app/* (experiencia de producto para el móvil).
Independientes de `models.py` (contrato oficial de /decide) — no se tocan
entre sí. Usan camelCase en la frontera HTTP porque así los consume
`mobile/services/api.ts`.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


Vehicle = Literal["bike", "moto", "car"]
Flexibility = Literal["strict", "balanced", "flexible"]

SessionState = Literal[
    "setup", "searching", "reviewing_offer", "confirming_order",
    "to_pickup", "waiting_pickup", "to_dropoff", "delivery_completed",
    "searching_next", "to_destination", "session_completed",
]


class GeoPointModel(CamelModel):
    latitude: float
    longitude: float
    label: str = ""


class CreateSessionRequest(CamelModel):
    current_location: GeoPointModel
    destination: GeoPointModel
    deadline: str  # ISO datetime
    flexibility: Flexibility
    vehicle: Vehicle


class RouteSegmentModel(CamelModel):
    type: Literal["to_pickup", "to_dropoff", "to_destination", "direct"]
    coordinates: list[GeoPointModel]
    distance_km: float
    duration_min: float
    traffic_delay_min: float


class RouteDataModel(CamelModel):
    provider: Literal["tomtom", "precomputed"]
    calculated_at: str
    total_distance_km: float
    total_duration_min: float
    traffic_delay_min: float
    segments: list[RouteSegmentModel]
    version: int


class MetricsModel(CamelModel):
    gross_earnings_mxn: float
    net_earnings_mxn: float
    orders_completed: int
    distance_km: float
    incidents_avoided: int


class SessionSnapshot(CamelModel):
    session_id: str
    current_location: GeoPointModel
    destination: GeoPointModel
    start_time: str
    deadline: str
    flexibility: Flexibility
    vehicle: Vehicle
    state: SessionState
    direct_route: RouteDataModel
    metrics: MetricsModel
    arrived_at_current_stop: bool = False


class RecommendationModel(CamelModel):
    order_id: str
    restaurant_name: str
    pickup_name: str
    dropoff_name: str
    gross_pay_mxn: float
    estimated_cost_mxn: float
    net_earnings_mxn: float
    additional_time_min: float
    additional_distance_km: float
    final_arrival_time: str
    reason: str
    expires_at: str
    available: bool
    route: RouteDataModel


class AcceptOrderResponse(CamelModel):
    success: bool
    message: Optional[str] = None
    state: SessionState
    route: Optional[RouteDataModel] = None
    recommendations: Optional[list[RecommendationModel]] = None


class SkipOrderResponse(CamelModel):
    recommendations: list[RecommendationModel]


class AdvanceRequest(CamelModel):
    elapsed_seconds: float = Field(gt=0)


class AdvanceEvent(CamelModel):
    type: str
    message: str
    severity: Literal["info", "warning", "danger"]


class AdvanceResponse(CamelModel):
    state: SessionState
    arrived_at_pickup: bool
    arrived_at_dropoff: bool
    arrived_at_destination: bool
    events: list[AdvanceEvent]
    route: Optional[RouteDataModel] = None
    metrics: MetricsModel


class PickupResponse(CamelModel):
    state: SessionState
    route: RouteDataModel


class DeliveryResponse(CamelModel):
    state: SessionState
    gross_pay_mxn: float
    cost_mxn: float
    net_earnings_mxn: float
    metrics: MetricsModel


class FinishResponse(CamelModel):
    state: SessionState
    arrived_on_time: bool
    metrics: MetricsModel
    arrival_time: str
