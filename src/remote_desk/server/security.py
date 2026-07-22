"""Controles de seguridad del servidor: rate-limiting y bloqueo por fuerza bruta."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class _Attempts:
    count: int = 0
    locked_until: float = 0.0


@dataclass
class LoginThrottle:
    """Limita intentos de clave fallidos por (ip, agent_id).

    Tras `max_attempts` fallos bloquea la combinacion durante `lockout_seconds`.
    """

    max_attempts: int
    lockout_seconds: int
    _attempts: dict[str, _Attempts] = field(default_factory=lambda: defaultdict(_Attempts))

    def _now(self) -> float:
        return time.monotonic()

    def is_locked(self, key: str) -> bool:
        entry = self._attempts.get(key)
        if entry is None:
            return False
        if entry.locked_until and self._now() < entry.locked_until:
            return True
        # Expiro el bloqueo: reiniciamos el contador.
        if entry.locked_until and self._now() >= entry.locked_until:
            self._attempts.pop(key, None)
        return False

    def record_failure(self, key: str) -> None:
        entry = self._attempts[key]
        entry.count += 1
        if entry.count >= self.max_attempts:
            entry.locked_until = self._now() + self.lockout_seconds

    def record_success(self, key: str) -> None:
        self._attempts.pop(key, None)
