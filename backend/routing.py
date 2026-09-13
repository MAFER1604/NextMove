"""
Interfaz RouteProvider con dos implementaciones:

  * MockRouteProvider: obligatoria, 100% determinista, sin red. Es la única
    que se usa dentro de /decide.
  * TomTomRouteProvider: opcional, solo para preparar/enriquecer escenarios
    ANTES de correr el turno (scenario_generator.py). Nunca se llama dentro
    del camino rápido de decisión.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from constraints.base import RouteEstimate
from datetime import datetime, timedelta

_VEHICLE_PROFILES_PATH = Path(__file__).parent / "config" / "vehicle_profiles.json"
_VEHICLE_PROFILES = json.loads(_VEHICLE_PROFILES_PATH.read_text(encoding="utf-8"))


@dataclass
class DirectRoute:
    time_min: float
    distance_km: float


class RouteProvider:
    def estimate_direct(self, from_zone: int, to_zone: int, vehicle: str) -> DirectRoute:
        raise NotImplementedError

    def estimate_candidate(
        self,
        current_zone: int,
        pickup_zone: int,
        dropoff_zone: int,
        final_destination_zone: int,
        vehicle: str,
        pickup_extra_min: float,
        dropoff_extra_min: float,
        restaurant_delay_min: float,
        traffic_multiplier: float,
        blocked_zones: set[int],
        sim_time: datetime,
    ) -> RouteEstimate:
        raise NotImplementedError


def _zone_distance_km(zone_a: int, zone_b: int) -> float:
    """Distancia determinista entre zonas: función simple y estable de sus
    identificadores (no depende de azar). Usada solo quando no se provee una
    distancia explícita en el evento (los pedidos reales SIEMPRE traen
    distance_pickup_km / distance_delivery_km del contrato oficial)."""
    if zone_a == zone_b:
        return 0.8
    return 1.2 + abs(zone_a - zone_b) * 0.9


class MockRouteProvider(RouteProvider):
    """Determinista: misma entrada -> misma salida, siempre. Sin I/O de red."""

    def estimate_direct(self, from_zone: int, to_zone: int, vehicle: str) -> DirectRoute:
        speed_kmh = _VEHICLE_PROFILES[vehicle]["speed_kmh"]
        dist = _zone_distance_km(from_zone, to_zone)
        time_min = (dist / speed_kmh) * 60.0
        return DirectRoute(time_min=round(time_min, 2), distance_km=round(dist, 3))

    def estimate_candidate(
        self,
        current_zone: int,
        pickup_zone: int,
        dropoff_zone: int,
        final_destination_zone: int,
        vehicle: str,
        pickup_extra_min: float,
        dropoff_extra_min: float,
        restaurant_delay_min: float,
        traffic_multiplier: float,
        blocked_zones: set[int],
        sim_time: datetime,
    ) -> RouteEstimate:
        speed_kmh = _VEHICLE_PROFILES[vehicle]["speed_kmh"]

        if pickup_zone in blocked_zones or dropoff_zone in blocked_zones:
            return RouteEstimate(
                pickup_min=0.0,
                dropoff_min=0.0,
                total_extra_time_min=0.0,
                total_extra_distance_km=0.0,
                arrival_at_final_destination=sim_time,
                blocked=True,
                block_reason=f"road closure blocks zone {pickup_zone if pickup_zone in blocked_zones else dropoff_zone}",
            )

        leg1 = _zone_distance_km(current_zone, pickup_zone)
        leg2 = _zone_distance_km(pickup_zone, dropoff_zone)
        leg3 = _zone_distance_km(dropoff_zone, final_destination_zone)
        direct = _zone_distance_km(current_zone, final_destination_zone)

        candidate_distance = leg1 + leg2 + leg3
        extra_distance = max(candidate_distance - direct, 0.0)

        transit_min = (candidate_distance / speed_kmh) * 60.0 * traffic_multiplier
        direct_transit_min = (direct / speed_kmh) * 60.0

        candidate_time = (
            transit_min
            + pickup_extra_min
            + dropoff_extra_min
            + restaurant_delay_min
        )
        extra_time = max(candidate_time - direct_transit_min, 1.0)

        arrival = sim_time + timedelta(minutes=candidate_time)

        return RouteEstimate(
            pickup_min=round(pickup_extra_min, 2),
            dropoff_min=round(dropoff_extra_min, 2),
            total_extra_time_min=round(extra_time, 2),
            total_extra_distance_km=round(extra_distance, 3),
            arrival_at_final_destination=arrival,
            blocked=False,
        )


class TomTomRouteProvider(RouteProvider):
    """OPCIONAL. Solo usada para preparar/enriquecer escenarios fuera del
    fast path (nunca dentro de /decide). Si no hay API key o falla la red,
    el llamador debe recurrir a MockRouteProvider; esta clase nunca debe
    hacer que el demo dependa de internet."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("TOMTOM_API_KEY", "")
        self.available = bool(self.api_key)

    def estimate_direct(self, from_zone: int, to_zone: int, vehicle: str) -> DirectRoute:
        raise RuntimeError(
            "TomTomRouteProvider no está implementado en este demo: requeriría "
            "coordenadas reales y una llamada de red. Usa MockRouteProvider."
        )

    def estimate_candidate(self, *args, **kwargs) -> RouteEstimate:
        raise RuntimeError(
            "TomTomRouteProvider no está implementado en este demo. Ver "
            "docstring de la clase."
        )
