"""Presupuesto de latencia: promedio, p50, p95 y máximo, sobre 1000 llamadas."""
import time

from decide import handle_decide
from models import DecideRequest

LATENCY_BUDGET_MS = 50

PAYLOAD = dict(
    order_id="ORD-LAT", platform="rappi", sim_time="2026-03-21T18:42:00",
    zone_pickup=7, zone_dropoff=11, distance_pickup_km=1.4, distance_delivery_km=6.5,
    base_pay_mxn=58.0, surge_multiplier=1.3, est_tip_mxn=12.0, restaurant_prep_min=9,
    weight_kg=2.1, volume_liters=6.0, vehicle="moto",
)


def test_decide_latency_budget_over_1000_calls():
    req = DecideRequest(**PAYLOAD)
    latencies_ms: list[float] = []
    for _ in range(1000):
        t0 = time.perf_counter()
        handle_decide(req)
        latencies_ms.append((time.perf_counter() - t0) * 1000)

    latencies_ms.sort()
    avg = sum(latencies_ms) / len(latencies_ms)
    p50 = latencies_ms[int(len(latencies_ms) * 0.50)]
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    worst = latencies_ms[-1]

    print(f"\n[latency] avg={avg:.3f}ms p50={p50:.3f}ms p95={p95:.3f}ms max={worst:.3f}ms")

    assert worst < LATENCY_BUDGET_MS, f"max latency {worst:.2f}ms exceeds {LATENCY_BUDGET_MS}ms budget"
    assert p95 < LATENCY_BUDGET_MS
    assert avg < LATENCY_BUDGET_MS
