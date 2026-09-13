"""
Ciclo de vida de sesión para /app/*. Cada sesión vive en su propia entrada
de un dict global keyed por session_id — muy distinto de "una única variable
global compartida entre todas las sesiones": dos sesiones nunca leen ni
escriben el estado de la otra, y borrar una no afecta a las demás. Esto se
prueba explícitamente en tests/test_app_endpoints.py
(test_two_sessions_stay_isolated).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import HTTPException

from geo import GeoPoint
from route_provider import RouteData

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "setup": {"searching"},
    "searching": {"reviewing_offer", "searching", "to_destination"},
    "reviewing_offer": {"confirming_order", "reviewing_offer", "searching"},
    "confirming_order": {"to_pickup", "reviewing_offer", "searching"},
    "to_pickup": {"waiting_pickup", "to_pickup"},
    "waiting_pickup": {"to_dropoff"},
    "to_dropoff": {"delivery_completed", "to_dropoff"},
    "delivery_completed": {"searching_next", "to_destination"},
    "searching_next": {"reviewing_offer", "searching_next", "to_destination"},
    "to_destination": {"session_completed", "to_destination"},
    "session_completed": set(),
}


@dataclass
class AppOffer:
    order_id: str
    restaurant_name: str
    pickup: GeoPoint
    dropoff: GeoPoint
    gross_pay_mxn: float
    weight_kg: float
    volume_l: float
    created_at: datetime
    expires_at: datetime
    status: str = "available"
    route: RouteData | None = None
    additional_time_min: float = 0.0
    additional_distance_km: float = 0.0
    reason: str = ""


@dataclass
class AppSession:
    session_id: str
    current_location: GeoPoint
    destination: GeoPoint
    start_time: datetime
    deadline: datetime
    flexibility: str
    vehicle: str
    state: str = "setup"
    gross_earnings_mxn: float = 0.0
    net_earnings_mxn: float = 0.0
    orders_completed: int = 0
    distance_km: float = 0.0
    incidents_avoided: int = 0
    continuous_riding_min: float = 0.0
    offers: dict[str, AppOffer] = field(default_factory=dict)
    offer_order: list[str] = field(default_factory=list)
    active_offer_id: str | None = None
    active_leg_elapsed_min: float = 0.0
    arrived_at_current_stop: bool = False
    direct_route: RouteData | None = None
    active_route: RouteData | None = None
    route_version: int = 0
    last_route_calc_at: datetime | None = None


_SESSIONS: dict[str, AppSession] = {}


def create_session(session: AppSession) -> None:
    _SESSIONS[session.session_id] = session


def get_session(session_id: str) -> AppSession:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    return session


def delete_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)


def new_session_id() -> str:
    return str(uuid.uuid4())[:12]


def transition(session: AppSession, new_state: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(session.state, set())
    if new_state not in allowed:
        raise HTTPException(409, f"cannot transition from '{session.state}' to '{new_state}'")
    session.state = new_state


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
