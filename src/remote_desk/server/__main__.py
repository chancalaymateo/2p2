"""Punto de entrada del servidor de senalizacion.

Uso:
    python -m remote_desk.server
    remote-desk-server   (si el paquete esta instalado)
"""

from __future__ import annotations

import asyncio

from remote_desk.common.config import AppConfig
from remote_desk.common.logging import setup_logging

from .app import SignalingServer

log = setup_logging("server")


def main() -> None:
    config = AppConfig.load()
    server = SignalingServer(config)
    try:
        asyncio.run(server.serve_forever())
    except KeyboardInterrupt:
        log.info("servidor detenido")


if __name__ == "__main__":
    main()
