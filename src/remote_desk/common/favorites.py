"""Conexiones favoritas del controlador (guardadas localmente).

Se persisten en `%LOCALAPPDATA%\\2p2\\favorites.json`. Guardamos alias + ID y,
opcionalmente, la clave (comodidad vs. seguridad: es decision del usuario).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from .paths import data_dir

_FAVORITES_FILE = "favorites.json"


@dataclass
class Favorite:
    alias: str
    agent_id: str
    password: str = ""  # opcional


@dataclass
class FavoritesStore:
    items: list[Favorite] = field(default_factory=list)

    # ------------------------------------------------------------- persistencia
    @classmethod
    def load(cls) -> "FavoritesStore":
        file = data_dir() / _FAVORITES_FILE
        if file.exists():
            try:
                raw = json.loads(file.read_text(encoding="utf-8"))
                return cls(items=[Favorite(**it) for it in raw])
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return cls()

    def save(self) -> None:
        file = data_dir() / _FAVORITES_FILE
        file.write_text(
            json.dumps([asdict(it) for it in self.items], indent=2), encoding="utf-8"
        )

    # -------------------------------------------------------------- operaciones
    def add(self, favorite: Favorite) -> None:
        # Reemplaza si ya existe uno con el mismo ID.
        self.remove(favorite.agent_id)
        self.items.append(favorite)
        self.save()

    def remove(self, agent_id: str) -> None:
        self.items = [it for it in self.items if it.agent_id != agent_id]
        self.save()

    def find(self, agent_id: str) -> Favorite | None:
        return next((it for it in self.items if it.agent_id == agent_id), None)
