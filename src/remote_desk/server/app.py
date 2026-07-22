"""Logica del servidor de senalizacion sobre WebSocket.

Responsabilidades:
  * Registrar agentes y asignarles ID + clave de sesion (con hash).
  * Emparejar controladores con agentes verificando la clave (rate-limited).
  * Retransmitir SDP/ICE entre ambos peers (el media va P2P, no pasa por aqui).

El servidor NUNCA ve el contenido de la sesion remota: solo intermedia el
handshake de WebRTC. El video y el input viajan cifrados P2P entre las maquinas.
"""

from __future__ import annotations

import ssl
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

from remote_desk.common import crypto
from remote_desk.common.config import AppConfig
from remote_desk.common.logging import setup_logging
from remote_desk.common.protocol import Signal, make, parse

from .registry import Agent, Registry, Session
from .security import LoginThrottle

log = setup_logging("server")


class SignalingServer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.registry = Registry()
        self.throttle = LoginThrottle(
            max_attempts=config.max_auth_attempts,
            lockout_seconds=config.auth_lockout_seconds,
        )

    # ------------------------------------------------------------------ ciclo
    async def handler(self, ws: WebSocketServerProtocol) -> None:
        peer = ws.remote_address[0] if ws.remote_address else "?"
        log.info("conexion nueva desde %s", peer)
        try:
            async for raw in ws:
                await self._dispatch(ws, peer, raw)
        except websockets.ConnectionClosed:
            pass
        finally:
            await self._cleanup(ws)

    async def _dispatch(self, ws: WebSocketServerProtocol, peer: str, raw: Any) -> None:
        try:
            msg = parse(raw)
        except ValueError as exc:
            await self._send(ws, Signal.ERROR, reason=str(exc))
            return

        handlers = {
            Signal.REGISTER_AGENT: self._on_register_agent,
            Signal.CONNECT_REQUEST: self._on_connect_request,
            Signal.ACCEPT_CONNECTION: self._on_accept_connection,
            Signal.REJECT_CONNECTION: self._on_reject_connection,
            Signal.WEBRTC_OFFER: self._on_relay,
            Signal.WEBRTC_ANSWER: self._on_relay,
            Signal.WEBRTC_ICE: self._on_relay,
        }
        handler = handlers.get(msg["type"])
        if handler is None:
            await self._send(ws, Signal.ERROR, reason=f"tipo desconocido: {msg['type']}")
            return
        await handler(ws, peer, msg)

    # --------------------------------------------------------------- handlers
    async def _on_register_agent(
        self, ws: WebSocketServerProtocol, peer: str, msg: dict
    ) -> None:
        # El agente propone su ID persistente y su identidad de dispositivo,
        # ademas del (salt, hash) de su clave. El servidor garantiza la unicidad.
        device_uuid = str(msg.get("device_uuid", ""))
        salt_hex = str(msg.get("salt", ""))
        hash_hex = str(msg.get("hash", ""))
        desired = crypto.normalize_id(str(msg.get("desired_id", "")))

        display_id, agent_id = self._grant_unique_id(desired, device_uuid)

        self.registry.add_agent(
            Agent(
                agent_id=agent_id,
                display_id=display_id,
                ws=ws,
                salt_hex=salt_hex,
                hash_hex=hash_hex,
                device_uuid=device_uuid,
            )
        )
        log.info("agente registrado: %s", display_id)
        # Devolvemos el ID concedido (puede diferir del deseado si hubo colision).
        await self._send(ws, Signal.AGENT_REGISTERED, agent_id=display_id)

    def _grant_unique_id(self, desired: str, device_uuid: str) -> tuple[str, str]:
        """Concede un ID unico entre los agentes conectados.

        Respeta el ID deseado si esta libre o pertenece al mismo dispositivo;
        de lo contrario genera uno nuevo garantizado unico. Devuelve (display, norm).
        """
        def fmt(norm: str) -> str:
            return f"{norm[0:3]} {norm[3:6]} {norm[6:9]}"

        if desired and len(desired) == 9:
            existing = self.registry.get_agent(desired)
            if existing is None or existing.device_uuid == device_uuid:
                return fmt(desired), desired

        # Colision (o sin ID deseado): asignamos uno nuevo libre.
        while True:
            candidate = crypto.normalize_id(crypto.generate_agent_id())
            if self.registry.get_agent(candidate) is None:
                return fmt(candidate), candidate

    async def _on_connect_request(
        self, ws: WebSocketServerProtocol, peer: str, msg: dict
    ) -> None:
        agent_id = crypto.normalize_id(str(msg.get("agent_id", "")))
        password = str(msg.get("password", ""))
        throttle_key = f"{peer}:{agent_id}"

        if self.throttle.is_locked(throttle_key):
            await self._send(ws, Signal.CONNECTION_REJECTED, reason="Demasiados intentos. Espera.")
            return

        agent = self.registry.get_agent(agent_id)
        if agent is None:
            self.throttle.record_failure(throttle_key)
            await self._send(ws, Signal.CONNECTION_REJECTED, reason="ID no encontrado.")
            return

        if not crypto.verify_password(password, agent.salt_hex, agent.hash_hex):
            self.throttle.record_failure(throttle_key)
            log.warning("clave incorrecta para %s desde %s", agent.display_id, peer)
            await self._send(ws, Signal.CONNECTION_REJECTED, reason="Clave incorrecta.")
            return

        self.throttle.record_success(throttle_key)
        token = crypto.generate_session_token()
        self.registry.add_session(
            Session(token=token, agent_id=agent_id, agent_ws=agent.ws, controller_ws=ws)
        )
        log.info("emparejamiento OK con %s (sesion %s)", agent.display_id, token[:8])
        # Pedimos consentimiento al agente antes de establecer el WebRTC.
        await self._send(
            agent.ws,
            Signal.INCOMING_CONNECTION,
            token=token,
            controller_ip=peer,
        )

    async def _on_accept_connection(
        self, ws: WebSocketServerProtocol, peer: str, msg: dict
    ) -> None:
        session = self.registry.get_session(str(msg.get("token", "")))
        if session is None or session.agent_ws is not ws:
            return
        ice = self.config.ice
        await self._send(
            session.controller_ws,
            Signal.CONNECTION_ACCEPTED,
            token=session.token,
            stun_urls=ice.stun_urls,
            turn_urls=ice.turn_urls,
            turn_username=ice.turn_username,
            turn_password=ice.turn_password,
        )

    async def _on_reject_connection(
        self, ws: WebSocketServerProtocol, peer: str, msg: dict
    ) -> None:
        session = self.registry.get_session(str(msg.get("token", "")))
        if session is None or session.agent_ws is not ws:
            return
        await self._send(
            session.controller_ws,
            Signal.CONNECTION_REJECTED,
            reason="El usuario remoto rechazo la conexion.",
        )
        self.registry.remove_session(session.token)

    async def _on_relay(self, ws: WebSocketServerProtocol, peer: str, msg: dict) -> None:
        """Retransmite offer/answer/ice al otro extremo de la sesion."""
        session = self.registry.get_session(str(msg.get("token", "")))
        if session is None:
            return
        target = (
            session.controller_ws if ws is session.agent_ws else session.agent_ws
        )
        await self._forward(target, msg)

    # ----------------------------------------------------------------- utils
    async def _send(self, ws: WebSocketServerProtocol, msg_type: str, **payload: Any) -> None:
        try:
            await ws.send(make(msg_type, **payload))
        except websockets.ConnectionClosed:
            pass

    async def _forward(self, ws: WebSocketServerProtocol, msg: dict) -> None:
        import json

        try:
            await ws.send(json.dumps(msg))
        except websockets.ConnectionClosed:
            pass

    async def _cleanup(self, ws: WebSocketServerProtocol) -> None:
        agent = self.registry.remove_agent_by_ws(ws)
        if agent:
            log.info("agente desconectado: %s", agent.display_id)

        session = self.registry.find_session_by_ws(ws)
        if session:
            other = (
                session.controller_ws if ws is session.agent_ws else session.agent_ws
            )
            await self._send(other, Signal.PEER_DISCONNECTED)
            self.registry.remove_session(session.token)

    # ------------------------------------------------------------------ serve
    def _build_ssl(self) -> ssl.SSLContext | None:
        if self.config.tls_cert_file and self.config.tls_key_file:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(self.config.tls_cert_file, self.config.tls_key_file)
            log.info("TLS habilitado (wss://)")
            return ctx
        log.warning("TLS deshabilitado: usando ws:// (solo para desarrollo local)")
        return None

    async def serve_forever(self) -> None:
        ssl_ctx = self._build_ssl()
        async with websockets.serve(
            self.handler,
            self.config.signaling_host,
            self.config.signaling_port,
            ssl=ssl_ctx,
            ping_interval=20,
            ping_timeout=20,
            max_size=2**20,
        ):
            scheme = "wss" if ssl_ctx else "ws"
            log.info(
                "servidor escuchando en %s://%s:%s",
                scheme,
                self.config.signaling_host,
                self.config.signaling_port,
            )
            import asyncio

            await asyncio.Future()  # corre indefinidamente
