"""
Replay determinista (sección 21 del prompt).

Reconstruye un turno desde su semilla/configuración (NO desde el archivo
JSONL, ya que el generador es la fuente de verdad determinista) y compara,
paso a paso, las decisiones ACCEPT/SKIP del agente NextMove contra las que
quedaron grabadas en la sesión original. No consulta TomTom, Claude, Ollama
ni la hora real; no usa datos nuevos.
"""
from __future__ import annotations

from datetime import datetime

from simulation_engine import SimulationSession, create_session, tick


def replay_session(original: SimulationSession, agent_name: str = "NextMove") -> dict:
    replay = create_session(
        seed=original.seed,
        shift_hours=(original.shift_end_time - original.agents[agent_name].config.sim_start_time).total_seconds() / 3600.0,
        vehicle=original.agents[agent_name].config.vehicle,
        start_location_zone=original.agents[agent_name].config.start_location_zone,
        final_destination_zone=original.final_destination_zone,
        scenario_kind=original.scenario_kind,
        sim_start_time=original.agents[agent_name].config.sim_start_time,
    )

    # Reproduce closures/surges exactamente igual: como create_session vuelve
    # a generar con la misma semilla, el flujo de eventos ya es idéntico.
    # Avanzamos el replay hasta completarlo, en pasos grandes para no gastar
    # tiempo real innecesario.
    step_min = 60.0
    while replay.status != "completed":
        tick(replay, step_min)

    original_decisions = [
        d for d in original.decision_log if d["agent"] == agent_name
    ]
    replay_decisions = [
        d for d in replay.decision_log if d["agent"] == agent_name
    ]

    for i, (o, r) in enumerate(zip(original_decisions, replay_decisions)):
        if o["order_id"] != r["order_id"] or o["decision"] != r["decision"]:
            return {
                "match": False,
                "first_difference": {
                    "index": i,
                    "original": {"order_id": o["order_id"], "decision": o["decision"]},
                    "replay": {"order_id": r["order_id"], "decision": r["decision"]},
                },
            }

    if len(original_decisions) != len(replay_decisions):
        return {
            "match": False,
            "first_difference": {
                "index": min(len(original_decisions), len(replay_decisions)),
                "detail": "decision count differs between original and replay",
            },
        }

    return {"match": True, "first_difference": None, "replay_session_id": replay.session_id}
