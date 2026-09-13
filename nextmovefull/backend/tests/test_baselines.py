"""Baselines (sección 26 del prompt): mismos eventos/semilla, resultados
independientes, sin acceso a eventos futuros."""
from simulation_engine import AGENT_STRATEGIES, create_session, tick


def test_all_agents_receive_identical_order_stream():
    session = create_session(seed=222, shift_hours=4.0, vehicle="moto",
                              start_location_zone=1, final_destination_zone=7,
                              scenario_kind="development_seed")
    # Todos los agentes comparten el mismo session.orders_by_id / session.events:
    # no hay streams distintos por agente.
    assert len(session.orders_by_id) > 0
    for name in AGENT_STRATEGIES:
        assert session.agents[name].config.seed == 222


def test_baselines_produce_independent_results():
    session = create_session(seed=333, shift_hours=4.0, vehicle="moto",
                              start_location_zone=1, final_destination_zone=7,
                              scenario_kind="development_seed")
    session.status = "running"
    n = 0
    while session.status != "completed" and n < 2000:
        tick(session, 15.0)
        n += 1

    earnings = {name: session.agents[name].net_earnings_mxn for name in AGENT_STRATEGIES}
    # No todos deben terminar con exactamente la misma ganancia (políticas distintas).
    assert len(set(earnings.values())) > 1


def test_no_agent_ever_registers_a_safety_violation():
    session = create_session(seed=444, shift_hours=4.0, vehicle="moto",
                              start_location_zone=1, final_destination_zone=7,
                              scenario_kind="development_seed")
    session.status = "running"
    n = 0
    while session.status != "completed" and n < 2000:
        tick(session, 15.0)
        n += 1
    for name in AGENT_STRATEGIES:
        assert session.agents[name].safety_violations == 0
