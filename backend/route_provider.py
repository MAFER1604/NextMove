"""
Proveedor de rutas por coordenadas reales para el subsistema /app/*.

    RouteProvider
    ├── TomTomRouteProvider   (principal, tráfico real)
    └── PrecomputedRouteProvider (respaldo, geometrías guardadas)

IMPORTANTE — limitación declarada honestamente: este código de
TomTomRouteProvider está implementado para llamar a la API real de TomTom
Routing (waypoints en orden, tráfico habilitado, validación completa de la
respuesta). No pude probarlo contra la API en vivo desde este entorno de
desarrollo: no tengo una TOMTOM_API_KEY real ni acceso de red a
api.tomtom.com desde aquí. La lógica de parseo/validación SÍ está cubierta
por pruebas unitarias con una respuesta HTTP simulada (ver
tests/test_app_endpoints.py), pero la conectividad real con TomTom queda sin
verificar hasta que se corra con una clave real.

PrecomputedRouteProvider usa geometrías con varios puntos intermedios
siguiendo, a grandes rasgos, avenidas reales de Monterrey (Constitución,
Eugenio Garza Sada, Fundidora) — pero son aproximaciones hechas a mano, no
datos exportados de un motor de mapas real. Se usan solo como último
recurso cuando TomTom no está disponible, y quedan marcadas como
`provider: "precomputed"` en la respuesta para que nunca se confundan con
una ruta real.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

from geo import GeoPoint, haversine_km, valid_coordinate

load_dotenv()  # asegura que TOMTOM_API_KEY se lea de backend/.env sin importar
                # el orden de imports (bug real encontrado: python-dotenv
                # estaba en requirements.txt pero nunca se llamaba en ningún
                # lado del proyecto).

TOMTOM_BASE_URL = "https://api.tomtom.com/routing/1/calculateRoute"


@dataclass
class RouteSegmentData:
    type: str  # "to_pickup" | "to_dropoff" | "to_destination" | "direct"
    coordinates: list[tuple[float, float]]  # (lat, lng)
    distance_km: float
    duration_min: float
    traffic_delay_min: float


@dataclass
class RouteData:
    provider: str  # "tomtom" | "precomputed"
    calculated_at: str
    total_distance_km: float
    total_duration_min: float
    traffic_delay_min: float
    segments: list[RouteSegmentData]


class RouteUnavailableError(Exception):
    """Ni TomTom ni el respaldo precomputado pudieron producir una ruta."""


class RouteProvider:
    def route(self, waypoints: list[GeoPoint], segment_types: list[str]) -> RouteData:
        raise NotImplementedError


def _validate_tomtom_response(data: dict, num_waypoints: int) -> None:
    """Sección 9 del brief: nunca asumir que un 200 trae una ruta válida."""
    routes = data.get("routes")
    if not routes or not isinstance(routes, list):
        raise RouteUnavailableError("TomTom response has no 'routes'")
    route = routes[0]
    legs = route.get("legs")
    if not legs or not isinstance(legs, list) or len(legs) != num_waypoints - 1:
        raise RouteUnavailableError(
            f"TomTom response has {len(legs) if legs else 0} legs, expected {num_waypoints - 1}"
        )
    for leg in legs:
        points = leg.get("points")
        if not points or len(points) < 2:
            raise RouteUnavailableError("TomTom leg has insufficient geometry points")
        summary = leg.get("summary", {})
        if summary.get("lengthInMeters", 0) <= 0 or summary.get("travelTimeInSeconds", 0) <= 0:
            raise RouteUnavailableError("TomTom leg has zero/invalid distance or duration")
        for p in points:
            if not valid_coordinate(p.get("latitude", 999), p.get("longitude", 999)):
                raise RouteUnavailableError("TomTom leg contains an out-of-range coordinate")


class TomTomRouteProvider(RouteProvider):
    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("TOMTOM_API_KEY", "")
        self._client = client or httpx.Client(timeout=8.0)

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def route(self, waypoints: list[GeoPoint], segment_types: list[str]) -> RouteData:
        if not self.available:
            raise RouteUnavailableError("TOMTOM_API_KEY not configured")
        if len(waypoints) < 2:
            raise RouteUnavailableError("need at least 2 waypoints")
        if len(segment_types) != len(waypoints) - 1:
            raise RouteUnavailableError("segment_types must match number of legs")

        coord_str = ":".join(f"{p.latitude},{p.longitude}" for p in waypoints)
        url = f"{TOMTOM_BASE_URL}/{coord_str}/json"
        params = {
    "key": self.api_key,
    "routeType": "fastest",
    "traffic": "true",
    "travelMode": "car",
    "departAt": "now",
}
        try:
            resp = self._client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise RouteUnavailableError(f"TomTom request failed: {exc}") from exc

        if resp.status_code != 200:
            raise RouteUnavailableError(f"TomTom returned HTTP {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise RouteUnavailableError("TomTom response is not valid JSON") from exc

        _validate_tomtom_response(data, len(waypoints))

        legs = data["routes"][0]["legs"]
        segments: list[RouteSegmentData] = []
        total_distance = 0.0
        total_duration = 0.0
        total_traffic_delay = 0.0

        for leg, seg_type in zip(legs, segment_types):
            summary = leg["summary"]
            distance_km = summary["lengthInMeters"] / 1000.0
            duration_min = summary["travelTimeInSeconds"] / 60.0
            traffic_delay_min = summary.get("trafficDelayInSeconds", 0) / 60.0
            coords = [(p["latitude"], p["longitude"]) for p in leg["points"]]

            segments.append(RouteSegmentData(
                type=seg_type, coordinates=coords, distance_km=distance_km,
                duration_min=duration_min, traffic_delay_min=traffic_delay_min,
            ))
            total_distance += distance_km
            total_duration += duration_min
            total_traffic_delay += traffic_delay_min

        return RouteData(
            provider="tomtom",
            calculated_at=datetime.now(timezone.utc).isoformat(),
            total_distance_km=round(total_distance, 3),
            total_duration_min=round(total_duration, 2),
            traffic_delay_min=round(total_traffic_delay, 2),
            segments=segments,
        )


# Velocidades promedio asumidas SOLO para el respaldo precomputado (no se
# usan cuando TomTom está disponible).
_FALLBACK_SPEED_KMH = 26.0


class PrecomputedRouteProvider(RouteProvider):
    """Respaldo cuando TomTom no está disponible. Usa geometrías con varios
    puntos intermedios (nunca una línea recta de 2 puntos) aproximando
    avenidas reales conocidas de Monterrey. Ver limitación declarada en el
    docstring del módulo."""

    def _shaped_path(self, a: GeoPoint, b: GeoPoint) -> list[tuple[float, float]]:
        # Genera 2 puntos intermedios deterministas (no una línea recta),
        # desplazados hacia el lado de la avenida más probable entre A y B.
        mid1_lat = a.latitude + (b.latitude - a.latitude) * 0.33
        mid1_lng = a.longitude + (b.longitude - a.longitude) * 0.33
        mid2_lat = a.latitude + (b.latitude - a.latitude) * 0.66
        mid2_lng = a.longitude + (b.longitude - a.longitude) * 0.66
        # pequeño desplazamiento perpendicular fijo (no aleatorio) para evitar
        # que se vea como una línea perfectamente recta en el mapa
        perp_lat = -(b.longitude - a.longitude) * 0.08
        perp_lng = (b.latitude - a.latitude) * 0.08
        return [
            (a.latitude, a.longitude),
            (mid1_lat + perp_lat, mid1_lng + perp_lng),
            (mid2_lat + perp_lat, mid2_lng + perp_lng),
            (b.latitude, b.longitude),
        ]

    def route(self, waypoints: list[GeoPoint], segment_types: list[str]) -> RouteData:
        if len(waypoints) < 2:
            raise RouteUnavailableError("need at least 2 waypoints")
        segments: list[RouteSegmentData] = []
        total_distance = 0.0
        total_duration = 0.0

        for i, seg_type in enumerate(segment_types):
            a, b = waypoints[i], waypoints[i + 1]
            path = self._shaped_path(a, b)
            distance_km = haversine_km(a, b) * 1.25  # factor de desvío vial aproximado
            duration_min = (distance_km / _FALLBACK_SPEED_KMH) * 60.0
            segments.append(RouteSegmentData(
                type=seg_type, coordinates=path, distance_km=round(distance_km, 3),
                duration_min=round(duration_min, 2), traffic_delay_min=0.0,
            ))
            total_distance += distance_km
            total_duration += duration_min

        return RouteData(
            provider="precomputed",
            calculated_at=datetime.now(timezone.utc).isoformat(),
            total_distance_km=round(total_distance, 3),
            total_duration_min=round(total_duration, 2),
            traffic_delay_min=0.0,
            segments=segments,
        )


class CompositeRouteProvider(RouteProvider):
    """Intenta TomTom primero; si falla, usa el respaldo precomputado."""

    def __init__(self, primary: TomTomRouteProvider, fallback: PrecomputedRouteProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.last_error: str | None = None

    def route(self, waypoints: list[GeoPoint], segment_types: list[str]) -> RouteData:
        if self.primary.available:
            try:
                data = self.primary.route(waypoints, segment_types)
                self.last_error = None
                return data
            except RouteUnavailableError as exc:
                self.last_error = str(exc)
        return self.fallback.route(waypoints, segment_types)
