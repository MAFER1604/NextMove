"""Determinismo (sección 6 y 26 del prompt)."""
from datetime import datetime

from decide import handle_decide
from deterministic_utils import dumps_event_log_line
from models import DecideRequest
from scenario_generator import generate_scenario


def test_same_seed_produces_byte_identical_event_stream():
    s1 = generate_scenario(seed=99, shift_hours=6.0, vehicle="car", start_location_zone=2,
                            sim_start_time=datetime(2026, 3, 21, 15, 0, 0))
    s2 = generate_scenario(seed=99, shift_hours=6.0, vehicle="car", start_location_zone=2,
                            sim_start_time=datetime(2026, 3, 21, 15, 0, 0))

    bytes1 = "\n".join(dumps_event_log_line(e) for e in s1.events).encode("utf-8")
    bytes2 = "\n".join(dumps_event_log_line(e) for e in s2.events).encode("utf-8")
    assert bytes1 == bytes2
    assert len(s1.events) > 0


def test_different_seeds_produce_different_streams():
    s1 = generate_scenario(seed=1, shift_hours=6.0, vehicle="car", start_location_zone=2,
                            sim_start_time=datetime(2026, 3, 21, 15, 0, 0))
    s2 = generate_scenario(seed=2, shift_hours=6.0, vehicle="car", start_location_zone=2,
                            sim_start_time=datetime(2026, 3, 21, 15, 0, 0))
    assert s1.events != s2.events


def test_same_input_produces_identical_decide_response():
    req = DecideRequest(
        order_id="ORD-DET", platform="rappi", sim_time="2026-03-21T18:42:00",
        zone_pickup=7, zone_dropoff=11, distance_pickup_km=1.4, distance_delivery_km=6.5,
        base_pay_mxn=58.0, surge_multiplier=1.3, est_tip_mxn=12.0, restaurant_prep_min=9,
        weight_kg=2.1, volume_liters=6.0, vehicle="moto",
    )
    r1 = handle_decide(req)
    r2 = handle_decide(req)
    assert r1.decision == r2.decision
    assert r1.reason == r2.reason
    assert r1.binding_constraint == r2.binding_constraint


def test_tick_granularity_does_not_change_outcome():
    """El resultado a una hora simulada dada no debe depender de en qué
    incrementos se llamó a tick() (ver bug corregido en simulation_engine)."""
    from simulation_engine import create_session, tick

    def run(step: float):
        s = create_session(seed=777, shift_hours=3.0, vehicle="moto",
                            start_location_zone=1, final_destination_zone=7,
                            scenario_kind="fixed_demo")
        s.status = "running"
        n = 0
        while s.status != "completed" and n < 2000:
            tick(s, step)
            n += 1
        return [(d["agent"], d["order_id"], d["decision"]) for d in s.decision_log]

    assert run(15.0) == run(60.0) == run(7.0)
