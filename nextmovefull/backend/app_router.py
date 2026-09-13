"""
Endpoints /app/* — backend como fuente de verdad para la experiencia móvil
real de NextMove (sección 4 del brief). El frontend nunca recalcula
puntuaciones ni decide viabilidad: todo pasa por aquí.

No duplica /decide ni el simulador de jueces (main.py original, routing.py,
scenario_generator.py) — es un subsistema aparte, montado bajo el prefijo
/app.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from app_models import (
    AcceptOrderResponse, AdvanceEvent, AdvanceRequest, AdvanceResponse,
    CreateSessionRequest, DeliveryResponse, FinishResponse, GeoPointModel,
    MetricsModel, PickupResponse, RecommendationModel, RouteDataModel,
    RouteSegmentModel, SessionSnapshot, SkipOrderResponse,
)
from app_session import (
    AppOffer, AppSession, delete_session as _delete_session, get_session,
    new_session_id, now_utc, transition,
)
from app_session import create_session as _store_session
from config.safety_limits import (
    DEFAULT_FUEL_MXN_PER_KM, VEHICLE_CAPACITY_KG, VEHICLE_CAPACITY_LITERS,
)
from geo import CITY_ANCHORS, GeoPoint, haversine_km
from route_provider import (
    CompositeRouteProvider, PrecomputedRouteProvider, RouteData, RouteUnavailableError,
    TomTomRouteProvider,
)

router = APIRouter(prefix="/app", tags=["app"])

_route_provider = CompositeRouteProvider(
    primary=TomTomRouteProvider(),
    fallback=PrecomputedRouteProvider(),
)

ROUTE_CACHE_TTL_SECONDS = 60
OFFER_EXPIRY_SECONDS = 60
RESTAURANT_NAMES = [
    "Tacos El Buen Sazón", "Sushi Roll Express", "Cafetería Aroma", "Burger House",
    "Pollo Feliz", "Pizza Nostra", "Mariscos La Costa", "Panadería San Ángel",
]


def _to_geo(p: GeoPointModel) -> GeoPoint:
    return GeoPoint(p.latitude, p.longitude, p.label)


def _route_to_model(data: RouteData) -> RouteDataModel:
    return RouteDataModel(
        provider=data.provider,
        calculatedAt=data.calculated_at,
        totalDistanceKm=data.total_distance_km,
        totalDurationMin=data.total_duration_min,
        trafficDelayMin=data.traffic_delay_min,
        version=0,
        segments=[
            RouteSegmentModel(
                type=seg.type,
                coordinates=[GeoPointModel(latitude=c[0], longitude=c[1], label="") for c in seg.coordinates],
                distanceKm=seg.distance_km,
                durationMin=seg.duration_min,
                trafficDelayMin=seg.traffic_delay_min,
            )
            for seg in data.segments
        ],
    )


def _metrics(session: AppSession) -> MetricsModel:
    return MetricsModel(
        grossEarningsMxn=round(session.gross_earnings_mxn, 2),
        netEarningsMxn=round(session.net_earnings_mxn, 2),
        ordersCompleted=session.orders_completed,
        distanceKm=round(session.distance_km, 2),
        incidentsAvoided=session.incidents_avoided,
    )


def _snapshot(session: AppSession) -> SessionSnapshot:
    return SessionSnapshot(
        sessionId=session.session_id,
        currentLocation=GeoPointModel(
            latitude=session.current_location.latitude,
            longitude=session.current_location.longitude,
            label=session.current_location.label,
        ),
        destination=GeoPointModel(
            latitude=session.destination.latitude,
            longitude=session.destination.longitude,
            label=session.destination.label,
        ),
        startTime=session.start_time.isoformat(),
        deadline=session.deadline.isoformat(),
        flexibility=session.flexibility,
        vehicle=session.vehicle,
        state=session.state,
        directRoute=_route_to_model(session.direct_route),
        metrics=_metrics(session),
        arrivedAtCurrentStop=session.arrived_at_current_stop,
    )


def _deadline_with_margin(session: AppSession) -> datetime:
    margin = {"strict": -10, "balanced": 0, "flexible": 10}[session.flexibility]
    return session.deadline + timedelta(minutes=margin)


def _pick_anchor_near(point: GeoPoint, exclude_label: str | None = None) -> GeoPoint:
    candidates = [a for a in CITY_ANCHORS.values() if a.label != exclude_label]
    candidates.sort(key=lambda a: haversine_km(point, a))
    pool = candidates[1:5] or candidates[:1]
    return random.choice(pool)


def _jitter(point: GeoPoint, km: float) -> GeoPoint:
    d_lat = random.uniform(-km, km) / 111.0
    d_lng = random.uniform(-km, km) / (111.0 * max(0.2, abs(math.cos(math.radians(point.latitude)))))
    return GeoPoint(point.latitude + d_lat, point.longitude + d_lng, point.label)


def _generate_offer(session: AppSession) -> AppOffer | None:
    pickup_anchor = _pick_anchor_near(session.current_location)
    pickup = _jitter(pickup_anchor, 0.7)
    dropoff_anchor = _pick_anchor_near(pickup, exclude_label=pickup_anchor.label)
    dropoff = _jitter(dropoff_anchor, 0.8)

    waypoints = [session.current_location, pickup, dropoff, session.destination]
    try:
        route = _route_provider.route(waypoints, ["to_pickup", "to_dropoff", "to_destination"])
    except RouteUnavailableError:
        return None

    direct = session.direct_route
    additional_time_min = max(route.total_duration_min - direct.total_duration_min, 1.0)
    additional_distance_km = max(route.total_distance_km - direct.total_distance_km, 0.0)

    gross_pay = round(random.uniform(35, 110), 0)
    weight_kg = round(random.uniform(0.3, 6.0), 1)
    volume_l = round(random.uniform(1.0, 14.0), 1)

    now = now_utc()
    final_arrival = now + timedelta(minutes=route.total_duration_min)

    hour = now.hour
    if (hour >= 22 or hour < 5) and additional_distance_km > 3:
        return None
    projected_riding = session.continuous_riding_min + additional_time_min * 0.4
    if projected_riding > 240:
        return None
    if 12 <= hour < 16 and projected_riding > 90:
        return None
    if weight_kg > VEHICLE_CAPACITY_KG[session.vehicle] or volume_l > VEHICLE_CAPACITY_LITERS[session.vehicle]:
        return None
    if final_arrival > _deadline_with_margin(session):
        return None

    order_id = f"ORD-{random.randint(1000, 9999)}"
    return AppOffer(
        order_id=order_id,
        restaurant_name=random.choice(RESTAURANT_NAMES),
        pickup=pickup,
        dropoff=dropoff,
        gross_pay_mxn=gross_pay,
        weight_kg=weight_kg,
        volume_l=volume_l,
        created_at=now,
        expires_at=now + timedelta(seconds=OFFER_EXPIRY_SECONDS),
        route=route,
        additional_time_min=round(additional_time_min, 1),
        additional_distance_km=round(additional_distance_km, 2),
        reason="This is the most profitable available order that keeps your arrival on time.",
    )


def _offer_to_recommendation(session: AppSession, offer: AppOffer) -> RecommendationModel:
    cost = round(offer.additional_distance_km * DEFAULT_FUEL_MXN_PER_KM[session.vehicle], 2)
    net = round(offer.gross_pay_mxn - cost, 2)
    final_arrival = offer.created_at + timedelta(minutes=offer.route.total_duration_min)
    return RecommendationModel(
        orderId=offer.order_id,
        restaurantName=offer.restaurant_name,
        pickupName=offer.pickup.label or "Pickup",
        dropoffName=offer.dropoff.label or "Drop-off",
        grossPayMxn=offer.gross_pay_mxn,
        estimatedCostMxn=cost,
        netEarningsMxn=net,
        additionalTimeMin=offer.additional_time_min,
        additionalDistanceKm=offer.additional_distance_km,
        finalArrivalTime=final_arrival.isoformat(),
        reason=offer.reason,
        expiresAt=offer.expires_at.isoformat(),
        available=offer.status == "available" and offer.expires_at > now_utc(),
        route=_route_to_model(offer.route),
    )


def _active_offers(session: AppSession) -> list[RecommendationModel]:
    now = now_utc()
    recs = []
    for oid in session.offer_order:
        offer = session.offers[oid]
        if offer.status == "available" and offer.expires_at <= now:
            offer.status = "expired"
        if offer.status == "available":
            recs.append(_offer_to_recommendation(session, offer))
    recs.sort(key=lambda r: r.net_earnings_mxn, reverse=True)
    return recs


@router.post("/sessions", response_model=SessionSnapshot)
def create_session_endpoint(req: CreateSessionRequest):
    now = now_utc()
    deadline = datetime.fromisoformat(req.deadline)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline < now:
        deadline = deadline + timedelta(days=1)

    current = _to_geo(req.current_location)
    destination = _to_geo(req.destination)

    try:
        direct = _route_provider.route([current, destination], ["direct"])
    except RouteUnavailableError as exc:
        raise HTTPException(503, f"Route temporarily unavailable: {exc}")

    session = AppSession(
        session_id=new_session_id(), current_location=current, destination=destination,
        start_time=now, deadline=deadline, flexibility=req.flexibility, vehicle=req.vehicle,
        state="setup", direct_route=direct, last_route_calc_at=now,
    )
    transition(session, "searching")
    _store_session(session)
    return _snapshot(session)


@router.get("/sessions/{session_id}", response_model=SessionSnapshot)
def get_session_snapshot(session_id: str):
    return _snapshot(get_session(session_id))


@router.get("/sessions/{session_id}/recommendations", response_model=list[RecommendationModel])
def get_recommendations(session_id: str):
    session = get_session(session_id)
    live = _active_offers(session)
    if not live:
        attempts = 0
        while len(live) < 3 and attempts < 8:
            attempts += 1
            offer = _generate_offer(session)
            if offer:
                session.offers[offer.order_id] = offer
                session.offer_order.append(offer.order_id)
                live.append(_offer_to_recommendation(session, offer))
        live.sort(key=lambda r: r.net_earnings_mxn, reverse=True)
    if session.state in ("searching", "searching_next"):
        transition(session, "reviewing_offer" if live else session.state)
    return live


@router.post("/sessions/{session_id}/orders/{order_id}/accept", response_model=AcceptOrderResponse)
def accept_order(session_id: str, order_id: str):
    session = get_session(session_id)
    offer = session.offers.get(order_id)
    if offer is None:
        raise HTTPException(404, "order not found")

    if offer.status != "available" or offer.expires_at <= now_utc():
        if offer.status == "available":
            offer.status = "expired"
        return AcceptOrderResponse(
            success=False,
            message="This order is no longer available. Here's your next best option.",
            state=session.state,
            recommendations=_active_offers(session),
        )

    offer.status = "accepted"
    session.active_offer_id = offer.order_id
    session.active_route = offer.route
    session.active_leg_elapsed_min = 0.0
    session.arrived_at_current_stop = False
    transition(session, "confirming_order")
    transition(session, "to_pickup")
    return AcceptOrderResponse(success=True, state=session.state, route=_route_to_model(offer.route))


@router.post("/sessions/{session_id}/orders/{order_id}/skip", response_model=SkipOrderResponse)
def skip_order(session_id: str, order_id: str):
    session = get_session(session_id)
    offer = session.offers.get(order_id)
    if offer and offer.status == "available":
        offer.status = "skipped"
    return SkipOrderResponse(recommendations=_active_offers(session))


@router.get("/sessions/{session_id}/route", response_model=RouteDataModel)
def get_route(session_id: str):
    session = get_session(session_id)
    route = session.active_route or session.direct_route
    return _route_to_model(route)


@router.post("/sessions/{session_id}/advance", response_model=AdvanceResponse)
def advance(session_id: str, req: AdvanceRequest):
    session = get_session(session_id)
    events: list[AdvanceEvent] = []
    arrived_pickup = arrived_dropoff = arrived_destination = False

    if session.state in ("to_pickup", "to_dropoff") and session.active_route:
        session.active_leg_elapsed_min += req.elapsed_seconds / 60.0
        segs = session.active_route.segments
        pickup_threshold = segs[0].duration_min
        dropoff_threshold = pickup_threshold + segs[1].duration_min

        if session.state == "to_pickup" and session.active_leg_elapsed_min >= pickup_threshold:
            arrived_pickup = True
            session.arrived_at_current_stop = True
            transition(session, "waiting_pickup")
        if session.state == "to_dropoff" and session.active_leg_elapsed_min >= dropoff_threshold:
            arrived_dropoff = True
            session.arrived_at_current_stop = True

        if random.random() < 0.05:
            events.append(AdvanceEvent(type="road_closure", message="Route updated", severity="info"))
            session.incidents_avoided += 1
        if session.state == "to_pickup" and random.random() < 0.03:
            events.append(AdvanceEvent(
                type="restaurant_delay",
                message="Restaurant delay. Your order will take 15 more minutes.",
                severity="warning",
            ))

    elif session.state == "to_destination":
        remaining_km = haversine_km(session.current_location, session.destination)
        if remaining_km < 0.25:
            arrived_destination = True
        else:
            speed_kmh = 26.0
            step_km = speed_kmh * (req.elapsed_seconds / 3600.0)
            frac = min(step_km / max(remaining_km, 0.01), 1.0)
            session.current_location = GeoPoint(
                session.current_location.latitude
                + (session.destination.latitude - session.current_location.latitude) * frac,
                session.current_location.longitude
                + (session.destination.longitude - session.current_location.longitude) * frac,
                session.current_location.label,
            )

    minutes_to_deadline = (_deadline_with_margin(session) - now_utc()).total_seconds() / 60.0
    if 0 < minutes_to_deadline < 12 and random.random() < 0.15:
        events.append(AdvanceEvent(type="arrival_risk", message="Your arrival time is coming up soon.", severity="danger"))

    return AdvanceResponse(
        state=session.state, arrivedAtPickup=arrived_pickup, arrivedAtDropoff=arrived_dropoff,
        arrivedAtDestination=arrived_destination, events=events,
        route=_route_to_model(session.active_route) if session.active_route else None,
        metrics=_metrics(session),
    )


@router.post("/sessions/{session_id}/pickup", response_model=PickupResponse)
def confirm_pickup(session_id: str):
    session = get_session(session_id)
    if session.state != "waiting_pickup":
        raise HTTPException(409, "cannot confirm pickup before arriving at the restaurant")
    transition(session, "to_dropoff")
    session.arrived_at_current_stop = False
    return PickupResponse(state=session.state, route=_route_to_model(session.active_route))


@router.post("/sessions/{session_id}/delivery", response_model=DeliveryResponse)
def confirm_delivery(session_id: str):
    session = get_session(session_id)
    if session.state != "to_dropoff" or not session.arrived_at_current_stop:
        raise HTTPException(409, "cannot confirm delivery before arriving at the drop-off")

    offer = session.offers[session.active_offer_id]
    cost = round(offer.additional_distance_km * DEFAULT_FUEL_MXN_PER_KM[session.vehicle], 2)
    net = round(offer.gross_pay_mxn - cost, 2)

    session.gross_earnings_mxn += offer.gross_pay_mxn
    session.net_earnings_mxn += net
    session.orders_completed += 1
    session.distance_km += offer.additional_distance_km
    session.continuous_riding_min += offer.additional_time_min * 0.4
    session.current_location = offer.dropoff
    session.active_offer_id = None
    session.active_route = None
    session.arrived_at_current_stop = False

    transition(session, "delivery_completed")
    return DeliveryResponse(
        state=session.state, grossPayMxn=offer.gross_pay_mxn, costMxn=cost, netEarningsMxn=net,
        metrics=_metrics(session),
    )


@router.post("/sessions/{session_id}/finish", response_model=FinishResponse)
def finish_session(session_id: str):
    session = get_session(session_id)
    if session.state == "delivery_completed":
        transition(session, "to_destination")
    if session.state == "searching_next":
        transition(session, "to_destination")
    if session.state == "to_destination":
        transition(session, "session_completed")
    elif session.state != "session_completed":
        raise HTTPException(409, f"cannot finish from state '{session.state}'")

    now = now_utc()
    on_time = now <= _deadline_with_margin(session)
    return FinishResponse(
        state=session.state, arrivedOnTime=on_time, metrics=_metrics(session),
        arrivalTime=now.isoformat(),
    )


@router.delete("/sessions/{session_id}")
def remove_session(session_id: str):
    _delete_session(session_id)
    return {"deleted": True}
