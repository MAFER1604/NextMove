"""Replay determinista (sección 21 y 26 del prompt)."""
from simulation_engine import create_session, tick
from replay_engine import replay_session


def _run_to_completion(seed: int) -> "SimulationSession":
    s = create_session(seed=seed, shift_hours=3.0, vehicle="moto",
                        start_location_zone=1, final_destination_zone=7,
                        scenario_kind="development_seed")
    s.status = "running"
    n = 0
    while s.status != "completed" and n < 2000:
        tick(s, 15.0)
        n += 1
    return s


def test_replay_matches_for_nextmove():
    session = _run_to_completion(seed=321)
    result = replay_session(session, agent_name="NextMove")
    assert result["match"] is True, result


def test_replay_matches_for_baseline():
    session = _run_to_completion(seed=654)
    result = replay_session(session, agent_name="HighestPay")
    assert result["match"] is True, result
