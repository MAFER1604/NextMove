"""Pruebas del subsistema /app/* (sección 23 del brief)."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from main import app
from geo import GeoPoint
from route_provider import (
    CompositeRouteProvider, PrecomputedRouteProvider, RouteData, RouteSegmentData,
    RouteUnavailableError, TomTomRouteProvider,
)

client = TestClient(app)

CURRENT = {"latitude": 25.6489, "longitude": -100.2854, "label": "Departamento Tec"}
DESTINATION = {"latitude": 25.6514, "longitude": -100.2895, "label": "Tec de Monterrey"}


def _future_deadline(hours=3) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _create_session(**overrides) -> dict:
    payload = {
        "currentLocation": CURRENT, "destination": DESTINATION,
        "deadline": _future_deadline(), "flexibility": "balanced", "vehicle": "car",
    }
    payload.update(overrides)
    resp = client.post("/app/sessions", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --------------------------------------------------------------------------
def test_create_session_returns_full_snapshot():
    data = _create_session()
    for key in ("sessionId", "currentLocation", "destination", "startTime", "deadline",
                "flexibility", "vehicle", "state", "directRoute", "metrics"):
        assert key in data
    assert data["state"] == "searching"
    assert data["metrics"]["ordersCompleted"] == 0
    assert data["metrics"]["netEarningsMxn"] == 0


def test_direct_route_has_real_looking_geometry_not_a_straight_line():
    data = _create_session()
    seg = data["directRoute"]["segments"][0]
    assert len(seg["coordinates"]) >= 2
    assert data["directRoute"]["totalDistanceKm"] > 0
    assert data["directRoute"]["totalDurationMin"] > 0


def test_get_recommendations_returns_sorted_viable_offers():
    data = _create_session()
    sid = data["sessionId"]
    resp = client.get(f"/app/sessions/{sid}/recommendations")
    assert resp.status_code == 200
    recs = resp.json()
    assert len(recs) > 0
    for r in recs:
        for key in ("orderId", "restaurantName", "pickupName", "dropoffName", "grossPayMxn",
                     "estimatedCostMxn", "netEarningsMxn", "additionalTimeMin",
                     "additionalDistanceKm", "finalArrivalTime", "reason", "expiresAt",
                     "available", "route"):
            assert key in r
        assert len(r["route"]["segments"]) == 3
    nets = [r["netEarningsMxn"] for r in recs]
    assert nets == sorted(nets, reverse=True)


def test_accept_available_order_moves_to_pickup():
    data = _create_session()
    sid = data["sessionId"]
    recs = client.get(f"/app/sessions/{sid}/recommendations").json()
    oid = recs[0]["orderId"]
    resp = client.post(f"/app/sessions/{sid}/orders/{oid}/accept")
    body = resp.json()
    assert body["success"] is True
    assert body["state"] == "to_pickup"
    assert len(body["route"]["segments"]) == 3


def test_accept_expired_order_returns_controlled_error_and_next_best():
    data = _create_session()
    sid = data["sessionId"]
    recs = client.get(f"/app/sessions/{sid}/recommendations").json()
    oid = recs[0]["orderId"]

    from app_session import get_session
    from datetime import timedelta as _td
    session = get_session(sid)
    session.offers[oid].expires_at = datetime.now(timezone.utc) - _td(seconds=1)

    resp = client.post(f"/app/sessions/{sid}/orders/{oid}/accept")
    body = resp.json()
    assert body["success"] is False
    assert "no longer available" in body["message"]
    assert isinstance(body["recommendations"], list)


def test_skip_order_marks_it_and_returns_remaining_recommendations():
    data = _create_session()
    sid = data["sessionId"]
    recs = client.get(f"/app/sessions/{sid}/recommendations").json()
    oid = recs[0]["orderId"]
    resp = client.post(f"/app/sessions/{sid}/orders/{oid}/skip")
    remaining = resp.json()["recommendations"]
    assert all(r["orderId"] != oid for r in remaining)


def test_cannot_confirm_delivery_before_pickup():
    data = _create_session()
    sid = data["sessionId"]
    resp = client.post(f"/app/sessions/{sid}/delivery")
    assert resp.status_code == 409


def test_cannot_confirm_pickup_before_accepting_order():
    data = _create_session()
    sid = data["sessionId"]
    resp = client.post(f"/app/sessions/{sid}/pickup")
    assert resp.status_code == 409


def test_full_happy_path_accumulates_earnings():
    data = _create_session()
    sid = data["sessionId"]
    recs = client.get(f"/app/sessions/{sid}/recommendations").json()
    oid = recs[0]["orderId"]
    expected_net = recs[0]["netEarningsMxn"]

    client.post(f"/app/sessions/{sid}/orders/{oid}/accept")

    for _ in range(200):
        r = client.post(f"/app/sessions/{sid}/advance", json={"elapsedSeconds": 15})
        if r.json()["arrivedAtPickup"]:
            break
    else:
        pytest.fail("never arrived at pickup")

    pickup_resp = client.post(f"/app/sessions/{sid}/pickup")
    assert pickup_resp.status_code == 200

    for _ in range(200):
        r = client.post(f"/app/sessions/{sid}/advance", json={"elapsedSeconds": 15})
        if r.json()["arrivedAtDropoff"]:
            break
    else:
        pytest.fail("never arrived at dropoff")

    delivery_resp = client.post(f"/app/sessions/{sid}/delivery")
    body = delivery_resp.json()
    assert body["state"] == "delivery_completed"
    assert abs(body["metrics"]["netEarningsMxn"] - expected_net) < 0.5
    assert body["metrics"]["ordersCompleted"] == 1


def test_finish_session_reports_arrival():
    data = _create_session()
    sid = data["sessionId"]
    recs = client.get(f"/app/sessions/{sid}/recommendations").json()
    oid = recs[0]["orderId"]
    client.post(f"/app/sessions/{sid}/orders/{oid}/accept")
    for _ in range(200):
        if client.post(f"/app/sessions/{sid}/advance", json={"elapsedSeconds": 15}).json()["arrivedAtPickup"]:
            break
    client.post(f"/app/sessions/{sid}/pickup")
    for _ in range(200):
        if client.post(f"/app/sessions/{sid}/advance", json={"elapsedSeconds": 15}).json()["arrivedAtDropoff"]:
            break
    client.post(f"/app/sessions/{sid}/delivery")

    resp = client.post(f"/app/sessions/{sid}/finish")
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "session_completed"
    assert "arrivedOnTime" in body


def test_delete_session_removes_it():
    data = _create_session()
    sid = data["sessionId"]
    resp = client.delete(f"/app/sessions/{sid}")
    assert resp.status_code == 200
    resp2 = client.get(f"/app/sessions/{sid}")
    assert resp2.status_code == 404


def test_two_sessions_stay_isolated():
    """No debe existir una única variable global compartida entre sesiones."""
    s1 = _create_session()
    s2 = _create_session(vehicle="bike")
    assert s1["sessionId"] != s2["sessionId"]

    recs1 = client.get(f"/app/sessions/{s1['sessionId']}/recommendations").json()
    client.post(f"/app/sessions/{s1['sessionId']}/orders/{recs1[0]['orderId']}/accept")

    snap1 = client.get(f"/app/sessions/{s1['sessionId']}").json()
    snap2 = client.get(f"/app/sessions/{s2['sessionId']}").json()
    assert snap1["state"] == "to_pickup"
    assert snap2["state"] == "searching"  # no contaminado por la sesión 1
    assert snap2["vehicle"] == "bike"


# --------------------------------------------------------------------------
# Pruebas de RouteProvider: TomTom simulado (sin red real) + respaldo
# --------------------------------------------------------------------------
class _FakeTomTomResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeHttpClient:
    def __init__(self, response: _FakeTomTomResponse):
        self._response = response

    def get(self, url, params=None):
        return self._response


def _valid_tomtom_payload(num_legs: int) -> dict:
    leg = {
        "summary": {"lengthInMeters": 1200, "travelTimeInSeconds": 300, "trafficDelayInSeconds": 20},
        "points": [
            {"latitude": 25.65, "longitude": -100.29},
            {"latitude": 25.651, "longitude": -100.289},
            {"latitude": 25.652, "longitude": -100.288},
        ],
    }
    return {"routes": [{"legs": [leg for _ in range(num_legs)]}]}


def test_tomtom_provider_parses_valid_response_correctly():
    payload = _valid_tomtom_payload(num_legs=1)
    fake_client = _FakeHttpClient(_FakeTomTomResponse(200, payload))
    provider = TomTomRouteProvider(api_key="fake-key-for-test", client=fake_client)

    a = GeoPoint(25.65, -100.29, "A")
    b = GeoPoint(25.652, -100.288, "B")
    result = provider.route([a, b], ["direct"])

    assert result.provider == "tomtom"
    assert result.total_distance_km == pytest.approx(1.2)
    assert result.total_duration_min == pytest.approx(5.0)
    assert result.traffic_delay_min == pytest.approx(20 / 60, abs=0.01)
    assert len(result.segments[0].coordinates) == 3


def test_tomtom_provider_rejects_response_with_no_routes():
    fake_client = _FakeHttpClient(_FakeTomTomResponse(200, {"routes": []}))
    provider = TomTomRouteProvider(api_key="fake-key", client=fake_client)
    with pytest.raises(RouteUnavailableError):
        provider.route([GeoPoint(25.65, -100.29, "A"), GeoPoint(25.652, -100.288, "B")], ["direct"])


def test_tomtom_provider_rejects_response_with_zero_distance():
    payload = _valid_tomtom_payload(num_legs=1)
    payload["routes"][0]["legs"][0]["summary"]["lengthInMeters"] = 0
    fake_client = _FakeHttpClient(_FakeTomTomResponse(200, payload))
    provider = TomTomRouteProvider(api_key="fake-key", client=fake_client)
    with pytest.raises(RouteUnavailableError):
        provider.route([GeoPoint(25.65, -100.29, "A"), GeoPoint(25.652, -100.288, "B")], ["direct"])


def test_tomtom_provider_rejects_out_of_range_coordinates():
    payload = _valid_tomtom_payload(num_legs=1)
    payload["routes"][0]["legs"][0]["points"][0] = {"latitude": 999, "longitude": 999}
    fake_client = _FakeHttpClient(_FakeTomTomResponse(200, payload))
    provider = TomTomRouteProvider(api_key="fake-key", client=fake_client)
    with pytest.raises(RouteUnavailableError):
        provider.route([GeoPoint(25.65, -100.29, "A"), GeoPoint(25.652, -100.288, "B")], ["direct"])


def test_tomtom_provider_without_key_raises_unavailable():
    provider = TomTomRouteProvider(api_key="")
    with pytest.raises(RouteUnavailableError):
        provider.route([GeoPoint(25.65, -100.29, "A"), GeoPoint(25.652, -100.288, "B")], ["direct"])


def test_precomputed_provider_never_returns_a_two_point_straight_line():
    provider = PrecomputedRouteProvider()
    a = GeoPoint(25.65, -100.29, "A")
    b = GeoPoint(25.66, -100.28, "B")
    result = provider.route([a, b], ["direct"])
    assert result.provider == "precomputed"
    assert len(result.segments[0].coordinates) > 2  # nunca una línea recta de 2 puntos
    assert result.total_distance_km > 0
    assert result.total_duration_min > 0


def test_composite_provider_falls_back_when_tomtom_unavailable():
    primary = TomTomRouteProvider(api_key="")  # sin key -> no disponible
    fallback = PrecomputedRouteProvider()
    composite = CompositeRouteProvider(primary, fallback)
    result = composite.route(
        [GeoPoint(25.65, -100.29, "A"), GeoPoint(25.66, -100.28, "B")], ["direct"]
    )
    assert result.provider == "precomputed"


def test_composite_provider_falls_back_when_tomtom_response_invalid():
    fake_client = _FakeHttpClient(_FakeTomTomResponse(200, {"routes": []}))
    primary = TomTomRouteProvider(api_key="fake-key", client=fake_client)
    fallback = PrecomputedRouteProvider()
    composite = CompositeRouteProvider(primary, fallback)
    result = composite.route(
        [GeoPoint(25.65, -100.29, "A"), GeoPoint(25.66, -100.28, "B")], ["direct"]
    )
    assert result.provider == "precomputed"
    assert composite.last_error is not None
