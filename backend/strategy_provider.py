"""
StrategyProvider (sección 17 del prompt).

El modelo (Claude/Ollama) SOLO se usa fuera del camino rápido de /decide:
- analizar sesiones terminadas
- proponer parámetros antes de iniciar
- resumir resultados
- generar una explicación extensa posterior
- recomendar ajustes para la siguiente sesión

El modelo NUNCA acepta/rechaza dentro de /decide, nunca crea ni ignora
restricciones, nunca se consulta dentro del presupuesto de 50 ms, y nunca
modifica silenciosamente la estrategia durante un replay.

Se guarda `last_known_strategy`, versionada, para que el sistema siga
decidiendo con la última estrategia válida si el modelo falla.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from config.safety_limits import DEFAULT_RESERVATION_WAGE_MXN_HR


@dataclass
class Strategy:
    version: int
    reservation_wage_mxn_hr: float = DEFAULT_RESERVATION_WAGE_MXN_HR
    use_future_value: bool = True
    reasoning: str = "default strategy, no model consulted yet"
    confidence: str = "n/a"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StrategyProvider:
    """Interfaz para la capa de estrategia. `simulate_failure()` /
    `recover()` permiten al demo forzar el modo degradado sin depender de
    desconectar internet de verdad."""

    def __init__(self) -> None:
        self._last_known_strategy = Strategy(version=1)
        self._forced_failure = False

    @property
    def model_configured(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY")) or bool(os.environ.get("OLLAMA_BASE_URL"))

    @property
    def is_available(self) -> bool:
        return self.model_configured and not self._forced_failure

    @property
    def last_known_strategy(self) -> Strategy:
        return self._last_known_strategy

    def simulate_failure(self) -> None:
        self._forced_failure = True

    def recover(self) -> None:
        self._forced_failure = False

    def propose_strategy(self, context: dict) -> Strategy:
        """Fuera del fast path. Si el modelo no está disponible (o se forzó
        la falla), NO lanza excepción: simplemente devuelve la última
        estrategia válida conocida y dej a quien llama marcar `degraded`."""
        if not self.is_available:
            return self._last_known_strategy

        # En este demo no se hace la llamada real de red a Claude/Ollama
        # (fuera de alcance de la capa de decisión); se deja el punto de
        # extensión documentado para no bloquear el demo sin credenciales.
        proposed = Strategy(
            version=self._last_known_strategy.version + 1,
            reservation_wage_mxn_hr=self._last_known_strategy.reservation_wage_mxn_hr,
            use_future_value=True,
            reasoning="strategy layer stub: wire ANTHROPIC_API_KEY/OLLAMA_BASE_URL calls here",
            confidence="n/a",
        )
        self._last_known_strategy = proposed
        return proposed

    def to_status_dict(self) -> dict:
        return {
            "model_status": "available" if self.is_available else "degraded",
            "last_known_strategy": asdict(self._last_known_strategy),
        }


strategy_provider_singleton = StrategyProvider()
