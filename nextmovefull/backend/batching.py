"""
Batching interno de NextMove (sección 13 del prompt).

El contrato oficial de /decide solo permite responder ACCEPT/SKIP sobre UNA
oferta (decision_response_schema.json). Por eso el batching vive únicamente
en el estado interno del agente (domain_models.CourierState.active_orders):
cuando NextMove ya tiene un pedido activo y llega un segundo candidato
compatible, el motor decide si conviene aceptarlo como parte de un batch,
pero la respuesta que sale por /decide sigue teniendo exactamente la forma
oficial (ACCEPT/SKIP sobre order_id).

Máximo 2 pedidos por batch. Se evalúan las secuencias válidas de
recogida/entrega (un pedido no puede entregarse antes de recogerse).
"""
from __future__ import annotations

from itertools import permutations

from domain_models import Order


def valid_pickup_dropoff_sequences(order_a: Order, order_b: Order) -> list[tuple[str, ...]]:
    """Todas las secuencias válidas de 4 eventos (pickup_a, dropoff_a,
    pickup_b, dropoff_b) tal que cada dropoff ocurre después de su pickup."""
    events = [("pickup", "A"), ("dropoff", "A"), ("pickup", "B"), ("dropoff", "B")]
    valid: list[tuple[str, ...]] = []
    for perm in permutations(events):
        idx = {ev: i for i, ev in enumerate(perm)}
        if idx[("pickup", "A")] < idx[("dropoff", "A")] and idx[("pickup", "B")] < idx[("dropoff", "B")]:
            valid.append(tuple(f"{kind}_{who}" for kind, who in perm))
    return valid


def combined_weight_volume(order_a: Order, order_b: Order) -> tuple[float, float]:
    return (order_a.weight_kg + order_b.weight_kg, order_a.volume_liters + order_b.volume_liters)


def can_batch(order_a: Order, order_b: Order, max_capacity_kg: float, max_capacity_liters: float) -> bool:
    if order_a.order_id == order_b.order_id:
        return False
    kg, liters = combined_weight_volume(order_a, order_b)
    return kg <= max_capacity_kg and liters <= max_capacity_liters
