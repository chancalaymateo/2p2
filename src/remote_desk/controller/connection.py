"""Capa de conexion del controlador (senalizacion + WebRTC como 'answerer').

Es un QObject: emite senales de Qt (frame_ready, status, error, closed) para que
la interfaz se actualice de forma reactiva sin acoplarse a la logica de red.

Flujo:
  1. Conecta al servidor y envia connect-request(ID, clave).
  2. Al recibir connection-accepted, espera la OFFER del agente.
  3. Aplica la OFFER, crea la ANSWER y la envia.
  4. Recibe la pista de video (on 'track') y el DataChannel de control.
  5. Un loop lee frames de video y los emite como QImage.
"""

from __future__ import annotations

import asyncio
import json

import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import candidate_from_sdp, candidate_to_sdp
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from remote_desk.common import crypto
from remote_desk.common.logging import setup_logging
from remote_desk.common.protocol import Signal as Sig
from remote_desk.common.protocol import make, parse
from remote_desk.common.webrtc import build_ice_servers

log = setup_logging("controller.connection")


class ControllerConnection(QObject):
    # Senales hacia la UI
    frame_ready = Signal(QImage)
    status = Signal(str)
    error = Signal(str)
    closed = Signal()

    def __init__(self, signaling_url: str) -> None:
        super().__init__()
        self._url = signaling_url
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._pc: RTCPeerConnection | None = None
        self._control = None  # DataChannel de control
        self._token: str | None = None
        self._tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------- API publica
    async def connect_to(self, agent_id: str, password: str) -> None:
        self.status.emit("Conectando al servidor...")
        self._ws = await websockets.connect(self._url, max_size=2**20)
        await self._ws.send(
            make(Sig.CONNECT_REQUEST, agent_id=crypto.normalize_id(agent_id), password=password)
        )
        self._spawn(self._recv_loop())

    def send_control(self, event: dict) -> None:
        """Envia un evento de mouse/teclado por el DataChannel (si esta abierto)."""
        if self._control and self._control.readyState == "open":
            try:
                self._control.send(json.dumps(event))
            except Exception:  # noqa: BLE001
                pass

    async def close(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._pc:
            await self._pc.close()
            self._pc = None
        if self._ws:
            await self._ws.close()
            self._ws = None

    # ------------------------------------------------------------- red interna
    def _spawn(self, coro) -> None:
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                try:
                    msg = parse(raw)
                except ValueError:
                    continue
                await self._on_message(msg)
        except websockets.ConnectionClosed:
            self.closed.emit()

    async def _on_message(self, msg: dict) -> None:
        mtype = msg["type"]

        if mtype == Sig.CONNECTION_ACCEPTED:
            self._token = msg["token"]
            self._create_peer(msg)
            self.status.emit("Autorizado. Estableciendo video...")

        elif mtype == Sig.CONNECTION_REJECTED:
            self.error.emit(msg.get("reason", "Conexion rechazada."))
            await self.close()

        elif mtype == Sig.WEBRTC_OFFER:
            await self._on_offer(msg)

        elif mtype == Sig.WEBRTC_ICE:
            await self._on_ice(msg)

        elif mtype == Sig.PEER_DISCONNECTED:
            self.status.emit("El equipo remoto se desconecto.")
            await self.close()
            self.closed.emit()

        elif mtype == Sig.ERROR:
            self.error.emit(msg.get("reason", "Error del servidor."))

    def _create_peer(self, accepted: dict) -> None:
        pc = RTCPeerConnection(
            build_ice_servers(
                accepted.get("stun_urls", []),
                accepted.get("turn_urls", []),
                accepted.get("turn_username", ""),
                accepted.get("turn_password", ""),
            )
        )
        self._pc = pc
        token = self._token

        @pc.on("track")
        def _on_track(track) -> None:  # noqa: ANN001, ANN202
            log.info("pista recibida: %s", track.kind)
            if track.kind == "video":
                self._spawn(self._consume_video(track))

        @pc.on("datachannel")
        def _on_datachannel(channel) -> None:  # noqa: ANN001, ANN202
            log.info("datachannel de control abierto: %s", channel.label)
            self._control = channel

        @pc.on("icecandidate")
        async def _on_local_ice(candidate) -> None:  # noqa: ANN001, ANN202
            if candidate and self._ws:
                await self._ws.send(
                    make(
                        Sig.WEBRTC_ICE,
                        token=token,
                        candidate=candidate_to_sdp(candidate),
                        sdpMid=candidate.sdpMid,
                        sdpMLineIndex=candidate.sdpMLineIndex,
                    )
                )

        @pc.on("connectionstatechange")
        async def _on_state() -> None:  # noqa: ANN202
            self.status.emit(f"WebRTC: {pc.connectionState}")
            if pc.connectionState == "connected":
                self.status.emit("Conectado")
            elif pc.connectionState in ("failed", "closed", "disconnected"):
                self.closed.emit()

    async def _on_offer(self, msg: dict) -> None:
        if not self._pc:
            return
        await self._pc.setRemoteDescription(
            RTCSessionDescription(sdp=msg["sdp"], type=msg["sdp_type"])
        )
        answer = await self._pc.createAnswer()
        await self._pc.setLocalDescription(answer)
        assert self._ws is not None
        await self._ws.send(
            make(
                Sig.WEBRTC_ANSWER,
                token=self._token,
                sdp=self._pc.localDescription.sdp,
                sdp_type=self._pc.localDescription.type,
            )
        )

    async def _on_ice(self, msg: dict) -> None:
        if not self._pc:
            return
        candidate = candidate_from_sdp(msg["candidate"])
        candidate.sdpMid = msg.get("sdpMid")
        candidate.sdpMLineIndex = msg.get("sdpMLineIndex")
        await self._pc.addIceCandidate(candidate)

    async def _consume_video(self, track) -> None:  # noqa: ANN001
        while True:
            try:
                frame = await track.recv()
            except Exception:  # noqa: BLE001 - fin de pista
                break
            arr = frame.to_ndarray(format="rgb24")
            h, w, _ = arr.shape
            # copy() para que QImage sea dueno de los datos (evita corrupcion).
            image = QImage(arr.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
            self.frame_ready.emit(image)
