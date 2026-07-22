"""Consentimiento del usuario del agente antes de aceptar una conexion.

Por seguridad, por defecto se pide confirmacion manual en la consola. En un
producto real esto seria un dialogo grafico del sistema. Se puede desactivar
(auto-aceptar) via AGENT_REQUIRE_CONSENT=false, util para maquinas desatendidas.
"""

from __future__ import annotations

import asyncio

from remote_desk.common.logging import setup_logging

log = setup_logging("agent.consent")


async def ask_consent(controller_ip: str, require_consent: bool) -> bool:
    """Devuelve True si se autoriza la conexion entrante."""
    if not require_consent:
        log.info("auto-aceptando conexion de %s (consentimiento desactivado)", controller_ip)
        return True

    prompt = (
        f"\n>>> Solicitud de control remoto desde {controller_ip}\n"
        f">>> Autorizar? [s/N]: "
    )
    # input() es bloqueante; lo ejecutamos en un hilo para no frenar el loop.
    answer = await asyncio.get_event_loop().run_in_executor(None, input, prompt)
    granted = answer.strip().lower() in ("s", "si", "y", "yes")
    log.info("conexion %s", "AUTORIZADA" if granted else "RECHAZADA")
    return granted
