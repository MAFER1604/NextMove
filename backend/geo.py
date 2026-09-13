"""
Utilidades geoespaciales y ubicaciones predefinidas para el subsistema de
producto (/app/*). Independiente del sistema de zonas usado por /decide y el
simulador de jueces (routing.py, scenario_generator.py) — no lo toca ni lo
reemplaza.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float
    label: str


PRESET_DESTINATIONS: dict[str, GeoPoint] = {
    "tec": GeoPoint(25.6514, -100.2895, "Tecnológico de Monterrey"),
    "paseo_tec": GeoPoint(25.6469, -100.2839, "Paseo Tec"),
    "nuevo_sur": GeoPoint(25.6398, -100.3157, "Nuevo Sur"),
    "fundidora": GeoPoint(25.6789, -100.2844, "Parque Fundidora"),
    "centro": GeoPoint(25.6714, -100.3095, "Centro de Monterrey"),
    "depto_tec": GeoPoint(25.6489, -100.2854, "Departamento Tec"),
}

PRESET_CURRENT_LOCATIONS: dict[str, GeoPoint] = {
    "depto_tec": GeoPoint(25.6489, -100.2854, "Departamento (Tec)"),
    "centro": GeoPoint(25.6714, -100.3095, "Centro de Monterrey"),
    "san_pedro": GeoPoint(25.6512, -100.4025, "San Pedro"),
    "valle_oriente": GeoPoint(25.6486, -100.3616, "Valle Oriente"),
    "mitras": GeoPoint(25.6842, -100.3564, "Mitras"),
}

# Anclas auxiliares para generar puntos de recogida/entrega plausibles.
CITY_ANCHORS: dict[str, GeoPoint] = {
    **PRESET_DESTINATIONS,
    **PRESET_CURRENT_LOCATIONS,
    "obispado": GeoPoint(25.6746, -100.3389, "Obispado"),
    "independencia": GeoPoint(25.6577, -100.3298, "Independencia"),
    "contry": GeoPoint(25.6355, -100.2825, "Contry"),
    "del_valle": GeoPoint(25.6489, -100.3762, "Del Valle"),
    "la_alianza": GeoPoint(25.6975, -100.2790, "La Alianza"),
}


def haversine_km(a: GeoPoint | tuple[float, float], b: GeoPoint | tuple[float, float]) -> float:
    lat1, lng1 = (a.latitude, a.longitude) if isinstance(a, GeoPoint) else a
    lat2, lng2 = (b.latitude, b.longitude) if isinstance(b, GeoPoint) else b
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a_ = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a_), math.sqrt(1 - a_))


def valid_coordinate(lat: float, lng: float) -> bool:
    """Rango válido de coordenadas reales, y aproximadamente dentro del área
    metropolitana de Monterrey (evita aceptar una geometría corrupta que caiga
    en otro continente por un parseo erróneo)."""
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return False
    return 25.3 <= lat <= 26.1 and -100.6 <= lng <= -99.9
