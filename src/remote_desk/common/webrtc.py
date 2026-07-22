"""Helpers compartidos de WebRTC (construccion de configuracion ICE)."""

from __future__ import annotations

from aiortc import RTCConfiguration, RTCIceServer


def build_ice_servers(
    stun_urls: list[str],
    turn_urls: list[str] | None = None,
    turn_username: str = "",
    turn_password: str = "",
) -> RTCConfiguration:
    """Crea una RTCConfiguration a partir de listas de URLs STUN/TURN."""
    servers: list[RTCIceServer] = []
    if stun_urls:
        servers.append(RTCIceServer(urls=stun_urls))
    if turn_urls:
        servers.append(
            RTCIceServer(
                urls=turn_urls,
                username=turn_username or None,
                credential=turn_password or None,
            )
        )
    return RTCConfiguration(iceServers=servers)
