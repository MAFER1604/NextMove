"""Pruebas del endpoint oficial POST /decide."""
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

BASE_PAYLOAD = {
    "order_id": "ORD-0001", "platform": "rappi", "sim_time": "2026-03-21T18:42:00",
    "zone_pickup": 7, "zone_dropoff": 11, "distance_pickup_km": 1.4,
    "distance_delivery_km": 6.5, "base_pay_mxn": 58.0, "surge_multiplier": 1.3,
    "est_tip_mxn": 12.0, "restaurant_prep_min": 9, "weight_kg": 2.1,
    "volume_liters": 6.0, "vehicle": "moto",
}


def test_decide_returns_required_fields():
    resp = client.post("/decide", json=BASE_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    for key in ("order_id", "decision", "reason", "latency_ms"):
        assert key in body
    assert body["decision"] in ("ACCEPT", "SKIP")


def test_decide_never_calls_network_stays_fast():
    import time

    t0 = time.perf_counter()
    resp = client.post("/decide", json=BASE_PAYLOAD)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert resp.status_code == 200
    # margen generoso para overhead de TestClient/HTTP; el presupuesto real
    # medido internamente (latency_ms del cuerpo) se valida en test_latency.py
    assert elapsed_ms < 500


def test_decide_vehicle_capacity_violation_is_skipped():
    payload = dict(BASE_PAYLOAD, order_id="ORD-HEAVY", weight_kg=999.0, volume_liters=999.0)
    resp = client.post("/decide", json=payload)
    body = resp.json()
    assert body["decision"] == "SKIP"
    assert body["binding_constraint"] == "vehicle_capacity"


def test_decide_courier_state_overrides_applied():
    payload = dict(BASE_PAYLOAD, order_id="ORD-BREAK")
    payload["courier_state_overrides"] = {"continuous_riding_min": 300}
    resp = client.post("/decide", json=payload)
    body = resp.json()
    assert body["decision"] == "SKIP"
    assert body["binding_constraint"] == "mandatory_break"


def test_decide_missing_optional_fields_does_not_crash():
    minimal = {
        "order_id": "ORD-MINIMAL", "sim_time": "2026-03-21T10:00:00",
        "zone_pickup": 1, "zone_dropoff": 2, "distance_pickup_km": 1.0,
        "distance_delivery_km": 2.0, "base_pay_mxn": 40.0, "surge_multiplier": 1.0,
        "vehicle": "car",
    }
    resp = client.post("/decide", json=minimal)
    assert resp.status_code == 200
