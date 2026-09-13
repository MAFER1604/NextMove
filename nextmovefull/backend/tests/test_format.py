"""Pruebas de FORMATO: el event log y las respuestas de /decide deben pasar
`contracts/validate_format.py`. Ver sección 26 del prompt."""
import json
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
VALIDATOR = BACKEND_DIR / "contracts" / "validate_format.py"


def _run_validator(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        capture_output=True, text=True, cwd=str(BACKEND_DIR),
    )


def test_generated_event_log_passes_validator(tmp_path):
    from simulation_engine import create_session, tick

    session = create_session(
        seed=555, shift_hours=2.0, vehicle="moto",
        start_location_zone=1, final_destination_zone=7, scenario_kind="development_seed",
    )
    session.status = "running"
    steps = 0
    while session.status != "completed" and steps < 500:
        tick(session, 15.0)
        steps += 1

    log_path = BACKEND_DIR / "outputs" / "event_logs" / f"{session.session_id}.jsonl"
    assert log_path.exists()

    result = _run_validator("--event-log", str(log_path))
    assert result.returncode == 0, result.stdout + result.stderr


def test_decide_responses_pass_validator(tmp_path):
    from decide import handle_decide
    from models import DecideRequest

    reqs = [
        DecideRequest(
            order_id=f"ORD-TEST-{i:03d}", platform="rappi", sim_time="2026-03-21T18:42:00",
            zone_pickup=7, zone_dropoff=11, distance_pickup_km=1.4, distance_delivery_km=6.5,
            base_pay_mxn=58.0, surge_multiplier=1.3, est_tip_mxn=12.0, restaurant_prep_min=9,
            weight_kg=2.1, volume_liters=6.0, vehicle="moto",
        )
        for i in range(5)
    ]
    responses = [handle_decide(r).model_dump(exclude_none=False) for r in reqs]

    out_path = tmp_path / "responses.json"
    out_path.write_text(json.dumps(responses))

    result = _run_validator("--responses", str(out_path))
    assert result.returncode == 0, result.stdout + result.stderr


def test_reason_is_under_40_words():
    from decide import handle_decide
    from models import DecideRequest

    req = DecideRequest(
        order_id="ORD-WORDCOUNT", platform="rappi", sim_time="2026-03-21T13:00:00",
        zone_pickup=3, zone_dropoff=3, distance_pickup_km=0.5, distance_delivery_km=1.0,
        base_pay_mxn=30.0, surge_multiplier=1.0, weight_kg=25.0, volume_liters=5.0, vehicle="bike",
    )
    resp = handle_decide(req)
    assert len(resp.reason.split()) <= 40
