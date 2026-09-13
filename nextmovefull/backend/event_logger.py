"""
Escribe el event log JSONL oficial (event_log_schema.json). Cada línea es un
evento único, en orden cronológico, serializado de forma determinista.
"""
from __future__ import annotations

from pathlib import Path

from deterministic_utils import dumps_event_log_line


class EventLogger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lines: list[str] = []

    def log(self, event: dict) -> None:
        self._lines.append(dumps_event_log_line(event))

    def flush(self) -> None:
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            for line in self._lines:
                f.write(line + "\n")

    @property
    def lines(self) -> list[str]:
        return list(self._lines)
