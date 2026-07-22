"""Configuracion central de logging para todos los componentes."""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def setup_logging(component: str) -> logging.Logger:
    """Configura y devuelve un logger para el componente dado.

    El nivel se controla con la variable de entorno LOG_LEVEL (por defecto INFO).
    """
    global _CONFIGURED
    if not _CONFIGURED:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        # aiortc y aioice son muy verbosos en DEBUG; los subimos un escalon.
        logging.getLogger("aioice").setLevel(logging.WARNING)
        logging.getLogger("aiortc").setLevel(logging.INFO)
        _CONFIGURED = True

    return logging.getLogger(f"remote-desk.{component}")
