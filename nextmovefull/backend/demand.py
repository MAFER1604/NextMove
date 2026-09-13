"""
Estimación de demanda futura, determinista, leída de data/demand.json.

future_value = probability_of_next_order * average_expected_net_earnings

Solo se aplica si queda tiempo suficiente para completar potencialmente otro
pedido y todavía llegar al destino final (verificado por el llamador en
scoring.py).
"""
from __future__ import annotations

import json
from pathlib import Path

_DEMAND_PATH = Path(__file__).parent / "data" / "demand.json"


class DemandModel:
    def __init__(self, path: Path = _DEMAND_PATH) -> None:
        self._table = json.loads(path.read_text(encoding="utf-8"))

    def _hour_bucket(self, hour: int) -> str:
        if 6 <= hour < 11:
            return "morning"
        if 11 <= hour < 15:
            return "midday"
        if 15 <= hour < 19:
            return "afternoon"
        if 19 <= hour < 23:
            return "evening"
        return "night"

    def future_value_mxn(self, zone: int, hour: int) -> float:
        bucket = self._hour_bucket(hour)
        zone_key = str(zone)
        entry = self._table.get(zone_key, {}).get(bucket)
        if entry is None:
            entry = self._table.get("default", {}).get(bucket, {"p": 0.0, "avg_net": 0.0})
        p = entry.get("p", 0.0)
        avg_net = entry.get("avg_net", 0.0)
        return round(p * avg_net, 2)
