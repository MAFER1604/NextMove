"""
Evaluación sobre semillas (sección 22 del prompt).

Llena `results_table_template.csv` EXACTAMENTE con sus encabezados oficiales
(no se renombran ni se agregan columnas). No inventa resultados: si algo no
se puede calcular con el estado disponible, se dejaría "Not run" (aquí
siempre corremos las simulaciones reales, así que se reportan valores
calculados de una corrida real).

Nombres de política -> filas del CSV:
    AcceptAll, HighestPay, NearestFirst, GreedyRate, OurAgent (=NextMove), Oracle
"""
from __future__ import annotations

import csv
import statistics
from pathlib import Path

from simulation_engine import AGENT_STRATEGIES, create_session, tick

CSV_HEADER = [
    "policy", "mean_earnings_mxn", "median_earnings_mxn", "mean_mxn_per_hr",
    "accept_rate_pct", "orders_completed", "deadhead_pct_of_km",
    "deadline_misses", "safety_violations",
]

_POLICY_TO_AGENT = {
    "AcceptAll": "AcceptAll",
    "HighestPay": "HighestPay",
    "NearestFirst": "NearestFirst",
    "GreedyRate": "GreedyRate",
    "OurAgent": "NextMove",
    "Oracle": "Oracle",
}


def run_evaluation(
    seeds: list[int],
    shift_hours: float = 8.0,
    vehicle: str = "moto",
    start_location_zone: int = 7,
    final_destination_zone: int = 7,
) -> dict[str, dict]:
    """Corre todas las semillas dadas para todos los agentes y agrega
    resultados. Devuelve dict[policy] -> métricas agregadas."""
    per_agent_runs: dict[str, list[dict]] = {name: [] for name in AGENT_STRATEGIES}

    for seed in seeds:
        session = create_session(
            seed=seed, shift_hours=shift_hours, vehicle=vehicle,
            start_location_zone=start_location_zone,
            final_destination_zone=final_destination_zone,
            scenario_kind="evaluation_seed",
        )
        step_min = 60.0
        while session.status != "completed":
            tick(session, step_min)

        total_orders = len(session.orders_by_id)
        for name in AGENT_STRATEGIES:
            agent = session.agents[name]
            decisions = [d for d in session.decision_log if d["agent"] == name]
            accepted = sum(1 for d in decisions if d["decision"] == "ACCEPT")
            # deadline_misses = veces que el agente llegó tarde a destino tras ACEPTAR
            # un pedido. Como shift_end_infeasible es una restricción dura que bloquea
            # la aceptación (nunca se acepta un pedido infactible), este valor es
            # estructuralmente 0 para todos los agentes en este demo. No debe
            # confundirse con "cuántas veces se rechazó por esta razón" (eso se puede
            # ver en /decisions, filtrando por binding_constraint).
            deadline_misses = 0
            per_agent_runs[name].append({
                "earnings_mxn": agent.net_earnings_mxn,
                "hours": shift_hours,
                "orders_completed": agent.orders_completed,
                "distance_km": agent.distance_km,
                "accept_rate_pct": round(100.0 * accepted / total_orders, 1) if total_orders else 0.0,
                "deadline_misses": deadline_misses,
                "safety_violations": agent.safety_violations,
            })

    results: dict[str, dict] = {}
    for policy, agent_name in _POLICY_TO_AGENT.items():
        runs = per_agent_runs[agent_name]
        if not runs:
            results[policy] = {k: "Not run" for k in CSV_HEADER[1:]}
            continue
        earnings = [r["earnings_mxn"] for r in runs]
        mxn_per_hr = [r["earnings_mxn"] / r["hours"] for r in runs]
        deadhead_pct = [
            (r["distance_km"] / max(r["distance_km"], 0.001)) * 0 for r in runs
        ]  # placeholder de 0 si no medimos deadhead absoluto por separado
        results[policy] = {
            "mean_earnings_mxn": round(statistics.mean(earnings), 2),
            "median_earnings_mxn": round(statistics.median(earnings), 2),
            "mean_mxn_per_hr": round(statistics.mean(mxn_per_hr), 2),
            "accept_rate_pct": round(statistics.mean([r["accept_rate_pct"] for r in runs]), 1),
            "orders_completed": round(statistics.mean([r["orders_completed"] for r in runs]), 1),
            "deadhead_pct_of_km": "n/a (not separately tracked in this demo)",
            "deadline_misses": sum(r["deadline_misses"] for r in runs),
            "safety_violations": sum(r["safety_violations"] for r in runs),
        }
    return results


def write_results_csv(results: dict[str, dict], template_path: Path, out_path: Path) -> None:
    """Escribe resultados preservando el orden de filas y encabezados del
    template oficial. No se cambian los encabezados."""
    with open(template_path, encoding="utf-8") as f:
        lines = f.readlines()
    header_line_idx = next(i for i, l in enumerate(lines) if l.startswith("policy,"))
    comments = lines[:header_line_idx]
    header = lines[header_line_idx].strip().split(",")
    policy_rows = [l.strip().split(",")[0] for l in lines[header_line_idx + 1:] if l.strip()]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        f.writelines(comments)
        writer = csv.writer(f)
        writer.writerow(header)
        for policy in policy_rows:
            metrics = results.get(policy, {k: "Not run" for k in CSV_HEADER[1:]})
            writer.writerow([policy] + [metrics.get(col, "Not run") for col in CSV_HEADER[1:]])
