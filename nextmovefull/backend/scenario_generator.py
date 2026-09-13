"""
Generador determinista de turnos.

Misma semilla -> mismos pedidos, tiempos, pagos, ubicaciones, eventos,
retrasos, surge y cierre vial, byte por byte (sección 6 del prompt).

No usa la hora real del sistema: todo se deriva de `sim_start_time` (fijo,
provisto por el llamador) y del RNG local instanciado con la semilla.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from deterministic_utils import make_rng, round_money, stable_order_id

_CONFIG_PATH = Path(__file__).parent / "config" / "simulation_config.json"
_SIM_CONFIG = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
_ZONE_NAMES: dict[str, str] = _SIM_CONFIG["zone_names"]
NUM_ZONES = _SIM_CONFIG["num_zones"]

PLATFORMS = ["rappi", "didi", "uber"]


@dataclass
class GeneratedScenario:
    events: list[dict]           # eventos listos para el event log (shift_start, order_offered, shock)
    seed: int
    shift_hours: float
    vehicle: str
    start_location_zone: int
    sim_start_time: datetime
    shift_end_time: datetime


def zone_name(zone: int) -> str:
    return _ZONE_NAMES.get(str(zone), f"Zone {zone}")


def generate_scenario(
    seed: int,
    shift_hours: float,
    vehicle: Literal["moto", "car", "bike"],
    start_location_zone: int,
    sim_start_time: datetime,
    num_zones: int = NUM_ZONES,
    target_num_orders: int | None = None,
) -> GeneratedScenario:
    rng = make_rng(seed)
    shift_end_time = sim_start_time + timedelta(hours=shift_hours)

    events: list[dict] = []
    events.append({
        "event": "shift_start",
        "sim_time": sim_start_time.isoformat(),
        "seed": seed,
        "shift_hours": shift_hours,
        "vehicle": vehicle,
        "start_location_zone": start_location_zone,
        "shift_end_time": shift_end_time.isoformat(),
        "fuel_mxn_per_km": {"bike": 0.0, "moto": 1.2, "car": 2.0}[vehicle],
    })

    total_minutes = shift_hours * 60
    if target_num_orders is None:
        # ~1 pedido cada 7-9 minutos simulados en promedio, determinista por semilla.
        target_num_orders = max(int(total_minutes / 8), 4)

    # Espaciar tiempos de llegada de pedidos de forma determinista (no exponencial
    # real para mantenerlo simple y reproducible con round() explícito).
    t = 6.0  # primer pedido a los 6 minutos de iniciado el turno
    order_index = 0
    surge_placed = False
    closure_placed = False
    delay_placed = False

    while t < total_minutes - 5 and order_index < target_num_orders:
        sim_time = sim_start_time + timedelta(minutes=round(t, 1))
        order_id = stable_order_id(seed, order_index)

        zone_pickup = 1 + rng.randrange(num_zones)
        zone_dropoff = 1 + rng.randrange(num_zones)
        if zone_dropoff == zone_pickup:
            zone_dropoff = 1 + ((zone_pickup) % num_zones)

        distance_pickup_km = round_money(0.4 + rng.random() * 3.2)
        distance_delivery_km = round_money(0.8 + rng.random() * 7.0)
        base_pay_mxn = round_money(25 + rng.random() * 60)
        est_tip_mxn = round_money(rng.random() * 20)
        surge_multiplier = 1.0
        restaurant_prep_min = round(5 + rng.random() * 10, 1)
        weight_kg = round(0.3 + rng.random() * 4.0, 1)
        volume_liters = round(1.0 + rng.random() * 10.0, 1)
        platform = PLATFORMS[rng.randrange(len(PLATFORMS))]

        # Ocasionalmente generar un pedido "trampa": pago alto pero que viola
        # una restricción de seguridad (para poder demostrarla en vivo).
        if order_index % 5 == 4:
            weight_kg = round(weight_kg + 20.0, 1)  # fuerza violación de capacidad
            base_pay_mxn = round_money(base_pay_mxn + 40)  # pago alto para tentar

        # El pedido "ancla" del retraso de restaurante de 15 min: se aplica el
        # slip directamente al prep_min de ESTE pedido antes de decidir, y
        # además se emite un evento `shock` (delay) para el log/banner.
        is_delay_anchor = (not delay_placed) and t >= total_minutes * 0.6
        if is_delay_anchor:
            restaurant_prep_min = round(restaurant_prep_min + 15.0, 1)

        events.append({
            "event": "order_offered",
            "order_id": order_id,
            "platform": platform,
            "sim_time": sim_time.isoformat(),
            "decision_deadline": (sim_time + timedelta(seconds=5)).isoformat(),
            "zone_pickup": zone_pickup,
            "zone_dropoff": zone_dropoff,
            "zone_pickup_name": zone_name(zone_pickup),
            "zone_dropoff_name": zone_name(zone_dropoff),
            "distance_pickup_km": distance_pickup_km,
            "distance_delivery_km": distance_delivery_km,
            "base_pay_mxn": base_pay_mxn,
            "est_tip_mxn": est_tip_mxn,
            "surge_multiplier": surge_multiplier,
            "restaurant_prep_min": restaurant_prep_min,
            "weight_kg": weight_kg,
            "volume_liters": volume_liters,
            "vehicle": vehicle,
        })

        # Shock: surge alrededor de 1/3 del turno.
        if not surge_placed and t >= total_minutes / 3:
            surge_zone = zone_dropoff
            events.append({
                "event": "shock", "sim_time": sim_time.isoformat(), "shock_type": "surge",
                "zone": surge_zone, "multiplier": 1.6, "duration_min": 25,
            })
            surge_placed = True

        # Shock: cierre vial alrededor de la mitad del turno.
        if not closure_placed and t >= total_minutes / 2:
            events.append({
                "event": "shock", "sim_time": sim_time.isoformat(), "shock_type": "closure",
                "zone": zone_pickup, "road": f"Av. Zone-{zone_pickup}", "duration_min": 30,
            })
            closure_placed = True

        # Shock: retraso de restaurante de 15 minutos, avanzado el turno.
        if is_delay_anchor:
            events.append({
                "event": "shock", "sim_time": sim_time.isoformat(), "shock_type": "delay",
                "order_id": order_id, "slip_min": 15,
            })
            delay_placed = True

        order_index += 1
        gap = 5 + rng.random() * 6
        t += gap

    # NOTA: el evento `shift_end` real (con orders_completed, earnings_mxn,
    # safety_violations reales) lo emite simulation_engine.py cuando el turno
    # efectivamente termina, no el generador — el generador solo produce el
    # flujo de pedidos y shocks, que es la parte que debe ser reproducible
    # byte por byte a partir de la semilla.

    _apply_surge_to_future_orders(events)

    return GeneratedScenario(
        events=events, seed=seed, shift_hours=shift_hours, vehicle=vehicle,
        start_location_zone=start_location_zone, sim_start_time=sim_start_time,
        shift_end_time=shift_end_time,
    )


def _apply_surge_to_future_orders(events: list[dict]) -> None:
    """Pasada post-generación, determinista: para cada shock de tipo surge,
    aplica su multiplicador a los pedidos posteriores cuyo zone_dropoff
    coincide con la zona del surge y cuyo sim_time cae dentro de la
    ventana [shock_time, shock_time + duration_min]."""
    surges = [e for e in events if e["event"] == "shock" and e["shock_type"] == "surge"]
    if not surges:
        return
    for surge in surges:
        surge_start = datetime.fromisoformat(surge["sim_time"])
        surge_end = surge_start + timedelta(minutes=surge["duration_min"])
        surge_zone = surge["zone"]
        multiplier = surge["multiplier"]
        for ev in events:
            if ev["event"] != "order_offered":
                continue
            ev_time = datetime.fromisoformat(ev["sim_time"])
            if ev["zone_dropoff"] == surge_zone and surge_start <= ev_time <= surge_end:
                ev["surge_multiplier"] = max(ev["surge_multiplier"], multiplier)
