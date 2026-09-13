"""Fallo del modelo (sección 17 y 26 del prompt): degradado, última
estrategia conocida, sin bloquear el fast path, dentro del presupuesto."""
import time

from strategy_provider import StrategyProvider


def test_model_available_by_default_without_env_keys(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    sp = StrategyProvider()
    assert sp.model_configured is False
    assert sp.is_available is False  # sin credenciales, se considera no disponible


def test_simulate_failure_sets_degraded_and_recover_clears_it(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    sp = StrategyProvider()
    assert sp.is_available is True

    sp.simulate_failure()
    assert sp.is_available is False
    status = sp.to_status_dict()
    assert status["model_status"] == "degraded"

    sp.recover()
    assert sp.is_available is True
    assert sp.to_status_dict()["model_status"] == "available"


def test_propose_strategy_falls_back_to_last_known_when_unavailable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    sp = StrategyProvider()
    before = sp.last_known_strategy
    proposed = sp.propose_strategy(context={})
    assert proposed is before  # no cambia silenciosamente sin modelo disponible


def test_decide_endpoint_never_depends_on_model_and_stays_fast():
    """El fast path de /decide nunca consulta el modelo, así que el fallo del
    modelo no debe afectar su latencia ni bloquearlo."""
    from decide import handle_decide
    from models import DecideRequest

    req = DecideRequest(
        order_id="ORD-DEGRADED", sim_time="2026-03-21T18:00:00", zone_pickup=2, zone_dropoff=2,
        distance_pickup_km=1.0, distance_delivery_km=2.0, base_pay_mxn=60.0, surge_multiplier=1.2,
        vehicle="moto",
    )
    t0 = time.perf_counter()
    resp = handle_decide(req)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 50
    assert resp.decision in ("ACCEPT", "SKIP")
