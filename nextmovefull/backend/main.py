"""
NextMove backend — FastAPI app.

Endpoint oficial prioritario: POST /decide (ver decide.py, models.py).
El resto son endpoints internos del demo (sección 20 del prompt), no parte
del contrato oficial de Infosys.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from decide import handle_decide
from evaluation import run_evaluation, write_results_csv
from models import DecideRequest, DecideResponse, ExplainDecisionResponse, AlternativeConsidered
from replay_engine import replay_session
from app_router import router as app_router
from simulation_engine import (
    AGENT_STRATEGIES,
    LIVE_DEMO_STRATEGIES,
    create_session,
    get_session,
    tick as engine_tick,
)
from strategy_provider import strategy_provider_singleton

DATA_DIR = Path(__file__).parent / "data"
CONTRACTS_DIR = Path(__file__).parent / "contracts"
OUTPUTS_DIR = Path(__file__).parent / "outputs"

app = FastAPI(title="NextMove backend", version="0.1.0")
app.include_router(app_router)

_cors_origins = os.environ.get("CORS_ALLOW_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _cors_origins == "*" else _cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# OFFICIAL ENDPOINT
# ---------------------------------------------------------------------------
@app.post("/decide", response_model=DecideResponse)
def decide(req: DecideRequest) -> DecideResponse:
    return handle_decide(req)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# Scenario / simulation lifecycle (internal, not part of the official contract)
# ---------------------------------------------------------------------------
class ScenarioGenerateRequest(BaseModel):
    seed: int
    shift_hours: float = 8.0
    vehicle: str = "moto"
    start_location_zone: int = 1
    final_destination_zone: int = 7
    scenario_kind: str = "development_seed"  # fixed_demo | development_seed | evaluation_seed


@app.post("/scenario/generate")
def scenario_generate(req: ScenarioGenerateRequest):
    session = create_session(
        seed=req.seed, shift_hours=req.shift_hours, vehicle=req.vehicle,
        start_location_zone=req.start_location_zone,
        final_destination_zone=req.final_destination_zone,
        scenario_kind=req.scenario_kind,
    )
    return {"session_id": session.session_id, "num_orders": len(session.orders_by_id),
            "shift_end_time": session.shift_end_time.isoformat()}


class SimulationStartRequest(BaseModel):
    session_id: str


@app.post("/simulation/start")
def simulation_start(req: SimulationStartRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    session.status = "running"
    return {"status": session.status}


class TickRequest(BaseModel):
    session_id: str
    advance_sim_minutes: float = 1.0


@app.post("/simulation/tick")
def simulation_tick(req: TickRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    if session.status != "running":
        return {"status": session.status, "banners": [], "sim_time": session.sim_clock.isoformat()}
    result = engine_tick(session, req.advance_sim_minutes * session.speed)
    return result


def _agent_public_state(agent) -> dict:
    return {
        "agent_id": agent.agent_id,
        "strategy": agent.strategy_name,
        "state": agent.state.value,
        "current_zone": agent.current_zone,
        "active_orders": [io.order.order_id for io in agent.active_orders],
        "gross_earnings_mxn": agent.gross_earnings_mxn,
        "operating_cost_mxn": agent.operating_cost_mxn,
        "net_earnings_mxn": agent.net_earnings_mxn,
        "distance_km": agent.distance_km,
        "orders_completed": agent.orders_completed,
        "late_deliveries": agent.late_deliveries,
        "incidents_avoided": agent.incidents_avoided,
        "last_decision": agent.last_decision,
        "model_status": agent.model_status.value,
        "safety_violations": agent.safety_violations,
    }


@app.get("/simulation/state")
def simulation_state(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    return {
        "session_id": session.session_id,
        "status": session.status,
        "sim_time": session.sim_clock.isoformat(),
        "shift_end_time": session.shift_end_time.isoformat(),
        "speed": session.speed,
        "scenario_kind": session.scenario_kind,
        "blocked_zones": list(session.blocked_zones.keys()),
        "agents": {name: _agent_public_state(session.agents[name]) for name in LIVE_DEMO_STRATEGIES},
        "strategy_status": session.strategy_provider.to_status_dict(),
    }


@app.post("/simulation/pause")
def simulation_pause(req: SimulationStartRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    session.status = "paused"
    return {"status": session.status}


@app.post("/simulation/resume")
def simulation_resume(req: SimulationStartRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    session.status = "running"
    return {"status": session.status}


@app.post("/simulation/reset")
def simulation_reset(req: SimulationStartRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    fresh = create_session(
        seed=session.seed,
        shift_hours=(session.shift_end_time - session.agents["NextMove"].config.sim_start_time).total_seconds() / 3600,
        vehicle=session.agents["NextMove"].config.vehicle,
        start_location_zone=session.agents["NextMove"].config.start_location_zone,
        final_destination_zone=session.final_destination_zone,
        scenario_kind=session.scenario_kind,
    )
    return {"session_id": fresh.session_id}


class SpeedRequest(BaseModel):
    session_id: str
    speed: int


@app.post("/simulation/speed")
def simulation_speed(req: SpeedRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    if req.speed not in (1, 2, 4):
        raise HTTPException(400, "speed must be 1, 2 or 4")
    session.speed = req.speed
    return {"speed": session.speed}


class IncidentRequest(BaseModel):
    session_id: str
    zone: int
    duration_min: float = 30.0


@app.post("/simulation/incident")
def simulation_incident(req: IncidentRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    from datetime import timedelta
    session.blocked_zones[req.zone] = session.sim_clock + timedelta(minutes=req.duration_min)
    return {"blocked_zones": list(session.blocked_zones.keys())}


class RestaurantDelayRequest(BaseModel):
    session_id: str
    order_id: str
    slip_min: float = 15.0


@app.post("/simulation/restaurant-delay")
def simulation_restaurant_delay(req: RestaurantDelayRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    order = session.orders_by_id.get(req.order_id)
    if order is None:
        raise HTTPException(404, "order not found")
    order.restaurant_prep_min += req.slip_min
    return {"order_id": req.order_id, "new_restaurant_prep_min": order.restaurant_prep_min}


@app.get("/simulation/results")
def simulation_results(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    return {
        "status": session.status,
        "agents": {name: _agent_public_state(session.agents[name]) for name in AGENT_STRATEGIES},
    }


# ---------------------------------------------------------------------------
# Decisions / explain_decision (official response shape)
# ---------------------------------------------------------------------------
@app.get("/decisions")
def list_decisions(session_id: str, agent: str | None = None, decision: str | None = None):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    rows = session.decision_log
    if agent:
        rows = [r for r in rows if r["agent"] == agent]
    if decision:
        rows = [r for r in rows if r["decision"] == decision]
    return {"decisions": rows}


@app.get("/decisions/{order_id}", response_model=ExplainDecisionResponse)
def explain_decision(order_id: str, session_id: str, agent: str = "NextMove"):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    matches = [r for r in session.decision_log if r["order_id"] == order_id and r["agent"] == agent]
    if not matches:
        raise HTTPException(404, "decision not found")
    record = matches[-1]
    return ExplainDecisionResponse(
        order_id=record["order_id"],
        decision=record["decision"],
        reason=record["reason"],
        inputs=record["inputs"],
        alternatives_considered=[
            AlternativeConsidered(**a) for a in record["alternatives_considered"]
        ],
    )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
class EvaluationRunRequest(BaseModel):
    seed_set: str = "evaluation"  # "development" | "evaluation"
    shift_hours: float = 8.0
    vehicle: str = "moto"
    start_location_zone: int = 1
    final_destination_zone: int = 7


@app.post("/evaluation/run")
def evaluation_run(req: EvaluationRunRequest):
    seeds_file = DATA_DIR / f"{req.seed_set}_seeds.json"
    if not seeds_file.exists():
        raise HTTPException(400, f"unknown seed_set {req.seed_set}")
    seeds = json.loads(seeds_file.read_text())["seeds"]

    results = run_evaluation(
        seeds=seeds, shift_hours=req.shift_hours, vehicle=req.vehicle,
        start_location_zone=req.start_location_zone,
        final_destination_zone=req.final_destination_zone,
    )
    out_csv = OUTPUTS_DIR / "results" / f"results_{req.seed_set}.csv"
    write_results_csv(results, CONTRACTS_DIR / "results_table_template.csv", out_csv)
    return {"seed_set": req.seed_set, "seeds_used": seeds, "results": results, "csv_path": str(out_csv)}


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------
class ReplayRequest(BaseModel):
    session_id: str
    agent: str = "NextMove"


@app.post("/replay")
def replay(req: ReplayRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    if session.status != "completed":
        raise HTTPException(400, "session must be completed before replay")
    result = replay_session(session, agent_name=req.agent)
    return result


@app.get("/replay/{replay_id}/diff")
def replay_diff(replay_id: str):
    session = get_session(replay_id)
    if session is None:
        raise HTTPException(404, "replay session not found")
    return {"session_id": replay_id, "status": session.status, "decisions": len(session.decision_log)}


# ---------------------------------------------------------------------------
# Model failure simulation (strategy layer only, never the fast path)
# ---------------------------------------------------------------------------
@app.post("/model/simulate-failure")
def model_simulate_failure():
    strategy_provider_singleton.simulate_failure()
    return strategy_provider_singleton.to_status_dict()


@app.post("/model/recover")
def model_recover():
    strategy_provider_singleton.recover()
    return strategy_provider_singleton.to_status_dict()
