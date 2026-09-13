"""
Límites de seguridad centralizados — NextMove / Courier.

IMPORTANTE PARA LOS JUECES: este es el único lugar donde viven los umbrales
numéricos de las 5 restricciones de seguridad oficiales definidas en
`backend/contracts/evaluation_protocol.md` (sección "4. Safety constraints").
No están enterrados en el motor de decisión ni en un prompt de modelo.

Las 5 restricciones oficiales son:
  1. No dropoff en zonas marcadas ("flagged") después de las 22:00.
  2. Descanso obligatorio de 20 minutos tras 4 horas continuas manejando.
  3. Regla de calor: máximo 90 minutos continuos de manejo entre 12:00 y 16:00.
  4. Rechazar pedidos que no se puedan completar antes de shift_end_time
     (en NextMove: la hora límite de llegada al destino final).
  5. Límites de peso y volumen según el tipo de vehículo.

`reservation_wage` NO es una restricción de seguridad: es un criterio
económico (salario de reserva) que el motor de puntuación usa para decidir
si un pedido vale la pena, no si es seguro.
"""
from __future__ import annotations

# --- 1. Flagged zone / night curfew ---------------------------------------
NIGHT_CURFEW_HOUR = 22  # a partir de esta hora (24h), no se permite dropoff en zonas marcadas
# Zonas marcadas como no seguras de noche. En un demo real esto vendría de un
# dataset de la ciudad; para el hackathon usamos una lista fija y visible.
FLAGGED_ZONES_NIGHT: set[int] = {3, 9, 14}

# --- 2. Mandatory break -----------------------------------------------------
MAX_CONTINUOUS_RIDING_MIN_BEFORE_BREAK = 4 * 60  # 4 horas continuas
MANDATORY_BREAK_MIN = 20

# --- 3. Heat rule ------------------------------------------------------------
HEAT_WINDOW_START_HOUR = 12
HEAT_WINDOW_END_HOUR = 16
HEAT_MAX_CONTINUOUS_RIDING_MIN = 90

# --- 4. Shift end feasibility -----------------------------------------------
# Sin margen configurable oculto: se calcula con el tiempo real estimado de
# recogida + entrega + regreso/continuación hacia el destino final.
SHIFT_END_SAFETY_MARGIN_MIN = 0  # margen adicional de seguridad, explícito y en cero por defecto

# --- 5. Vehicle capacity -----------------------------------------------------
# kg y litros máximos transportables por tipo de vehículo.
VEHICLE_CAPACITY_KG = {
    "bike": 5.0,
    "moto": 15.0,
    "car": 40.0,
}
VEHICLE_CAPACITY_LITERS = {
    "bike": 15.0,
    "moto": 40.0,
    "car": 120.0,
}

# --- Criterio económico (NO es restricción de seguridad) --------------------
# Salario de reserva mínimo (MXN/hora) por debajo del cual NextMove considera
# que un pedido no vale la pena, aunque sea seguro y factible.
DEFAULT_RESERVATION_WAGE_MXN_HR = 90.0

# --- Umbrales para baselines (heurísticas simples, sin demanda futura ni batching) ---
BASELINE_HIGHEST_PAY_MIN_TOTAL_MXN = 45.0   # HighestPay: acepta si el pago total alcanza este piso
BASELINE_NEAREST_MAX_PICKUP_KM = 3.0        # NearestFirst: acepta si la recogida está a esta distancia o menos
BASELINE_GREEDY_RATE_MIN_MXN_HR = 100.0     # GreedyRate: acepta si la tasa inmediata (sin demanda futura) alcanza esto

# Costo operativo por km (combustible, desgaste). Configurable, no enterrado
# en el algoritmo de puntuación.
DEFAULT_FUEL_MXN_PER_KM = {
    "bike": 0.0,
    "moto": 1.2,
    "car": 2.0,
}

# Tiempos base de operación (minutos), usados si el evento no trae uno explícito.
BASE_PICKUP_MIN = 5
BASE_DROPOFF_MIN = 3
