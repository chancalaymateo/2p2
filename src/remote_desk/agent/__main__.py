"""Punto de entrada del agente.

Uso:
    python -m remote_desk.agent
    remote-desk-agent   (si el paquete esta instalado)
"""

from __future__ import annotations

import asyncio

from remote_desk.common.config import AppConfig
from remote_desk.common.logging import setup_logging

from .connection import AgentClient

log = setup_logging("agent")


def main() -> None:
    config = AppConfig.load()
    client = AgentClient(config)
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        log.info("agente detenido")


if __name__ == "__main__":
    main()
