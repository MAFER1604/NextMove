"""
Utilidades para garantizar determinismo byte-a-byte en NextMove.

Reglas seguidas aquí (ver evaluation_protocol.md sección 1 y 6):
  * Nunca usar time.time() / datetime.now() para generar un turno.
  * Un único generador aleatorio local (nunca el módulo `random` global).
  * Redondeo explícito y centralizado antes de comparar o serializar.
  * Serialización JSON con claves ordenadas, separadores fijos y UTF-8.
"""
from __future__ import annotations

import json
import random
from typing import Any

ROUND_DECIMALS_MONEY = 2
ROUND_DECIMALS_TIME_MIN = 2
ROUND_DECIMALS_DISTANCE_KM = 3


def make_rng(seed: int) -> random.Random:
    """Instancia de RNG completamente local a la semilla. Nunca compartir
    estado entre turnos ni usar random.seed() global."""
    return random.Random(seed)


def round_money(x: float) -> float:
    return round(x + 0.0, ROUND_DECIMALS_MONEY)


def round_time_min(x: float) -> float:
    return round(x + 0.0, ROUND_DECIMALS_TIME_MIN)


def round_distance_km(x: float) -> float:
    return round(x + 0.0, ROUND_DECIMALS_DISTANCE_KM)


def stable_order_id(seed: int, index: int) -> str:
    """IDs derivados exclusivamente de semilla + índice, nunca de tiempo real
    o de un contador global mutable entre corridas."""
    return f"ORD-{seed:04d}-{index:04d}"


def dumps_stable(obj: Any) -> str:
    """Serialización JSON determinista: claves ordenadas, separadores fijos,
    sin espacios ambiguos, para que la misma semilla produzca el mismo
    archivo byte por byte."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def dumps_event_log_line(obj: dict) -> str:
    """Para el event log usamos el orden de inserción del dict (no sort_keys)
    porque el ejemplo oficial (`event_log_example.jsonl`) preserva un orden de
    campos legible para humanos; lo que debe ser estable es el CONTENIDO y la
    codificación, no el orden alfabético. Cada llamada con los mismos datos de
    entrada produce exactamente la misma línea."""
    return json.dumps(obj, ensure_ascii=False, separators=(", ", ": "))


def tie_break_key(alt) -> tuple:
    """Política central de desempate determinista (sección 12 del prompt):
    1) mayor expected_value, 2) mayor net_pay, 3) menor additional_time,
    4) menor additional_distance, 5) menor id alfanumérico.
    Se usa como key de ordenamiento DESCENDENTE en score, así que invertimos
    signos donde "mayor es mejor" y dejamos positivo donde "menor es mejor".
    """
    ids_joined = ",".join(alt.order_ids)
    return (
        -round_money(alt.expected_value_mxn),
        -round_money(alt.net_pay_mxn),
        round_time_min(alt.additional_time_min),
        round_distance_km(alt.additional_distance_km),
        ids_joined,
    )
