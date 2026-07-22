"""Cliente del agente: se conecta al servidor, negocia WebRTC y sirve la pantalla.

Flujo:
  1. Conecta al servidor de senalizacion y se registra -> recibe ID + clave.
  2. Espera una conexion entrante y pide consentimiento.
  3. Si se autoriza, crea el RTCPeerConnection: agrega la pista de pantalla y un
     DataChannel de control, genera la OFFER y la envia (relay via servidor).
  4. Aplica la ANSWER y los ICE candidates del controlador.
  5. Los eventos de mouse/teclado llegan por el DataChannel y se inyectan.
"""

from __future__ import annotations

import asyncio

import websockets
from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import candidate_from_sdp, candidate_to_sdp

from remote_desk.common import protocol
from remote_desk.common.config import AppConfig
from remote_desk.common.logging import setup_logging
from remote_desk.common.protocol import Signal, make, parse
from remote_desk.common.webrtc import build_ice_servers

from .capture import ScreenTrack
from .consent import ask_consent
from .input_controller import InputController

log = setup_logging("agent.connection")


class AgentClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._pc: RTCPeerConnection | None = None
        self._screen: ScreenTrack | None = None
        self._token: str | None = None

    async def run(self) -> None:
        log.info("conectando al servidor %s ...", self.config.signaling_url)
        async with websockets.connect(self.config.signaling_url, max_size=2**20) as ws:
            self._ws = ws
            await ws.send(make(Signal.REGISTER_AGENT))
            async for raw in ws:
                try:
                    msg = parse(raw)
                except ValueError:
                    continue
                await self._on_message(msg)

    async def _on_message(self, msg: dict) -> None:
        mtype = msg["type"]

        if mtype == Signal.AGENT_REGISTERED:
            self._print_credentials(msg["agent_id"], msg["password"])

        elif mtype == Signal.INCOMING_CONNECTION:
            await self._on_incoming(msg)

        elif mtype == Signal.WEBRTC_ANSWER:
            await self._on_answer(msg)

        elif mtype == Signal.WEBRTC_ICE:
            await self._on_ice(msg)

        elif mtype == Signal.PEER_DISCONNECTED:
            log.info("el controlador se desconecto")
            await self._teardown()

        elif mtype == Signal.ERROR:
            log.error("error del servidor: %s", msg.get("reason"))

    # ------------------------------------------------------------- handshake
    async def _on_incoming(self, msg: dict) -> None:
        token = msg["token"]
        controller_ip = msg.get("controller_ip", "?")

        granted = await ask_consent(controller_ip, self.config.agent_require_consent)
        assert self._ws is not None
        if not granted:
            await self._ws.send(make(Signal.REJECT_CONNECTION, token=token))
            return

        await self._ws.send(make(Signal.ACCEPT_CONNECTION, token=token))
        self._token = token
        await self._start_webrtc(token)

    async def _start_webrtc(self, token: str) -> None:
        ice = self.config.ice
        self._pc = RTCPeerConnection(
            build_ice_servers(ice.stun_urls, ice.turn_urls, ice.turn_username, ice.turn_password)
        )
        pc = self._pc

        # 1) Pista de pantalla (media saliente agente -> controlador).
        self._screen = ScreenTrack()
        pc.addTrack(self._screen)

        # 2) DataChannel de control (input entrante controlador -> agente).
        injector = InputController(self._screen.width, self._screen.height)
        channel = pc.createDataChannel("control", ordered=True)

        @channel.on("message")
        def _on_control(raw: str) -> None:  # noqa: ANN202
            try:
                injector.handle(parse(raw))
            except ValueError:
                pass

        @pc.on("icecandidate")
        async def _on_local_ice(candidate) -> None:  # noqa: ANN001, ANN202
            if candidate and self._ws:
                await self._ws.send(
                    make(
                        Signal.WEBRTC_ICE,
                        token=token,
                        candidate=candidate_to_sdp(candidate),
                        sdpMid=candidate.sdpMid,
                        sdpMLineIndex=candidate.sdpMLineIndex,
                    )
                )

        @pc.on("connectionstatechange")
        async def _on_state() -> None:  # noqa: ANN202
            log.info("estado WebRTC: %s", pc.connectionState)
            if pc.connectionState in ("failed", "closed", "disconnected"):
                await self._teardown()

        # 3) Generamos y enviamos la OFFER.
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        assert self._ws is not None
        await self._ws.send(
            make(
                Signal.WEBRTC_OFFER,
                token=token,
                sdp=pc.localDescription.sdp,
                sdp_type=pc.localDescription.type,
            )
        )
        log.info("offer enviada, esperando answer...")

    async def _on_answer(self, msg: dict) -> None:
        if not self._pc:
            return
        await self._pc.setRemoteDescription(
            RTCSessionDescription(sdp=msg["sdp"], type=msg["sdp_type"])
        )
        log.info("answer aplicada; sesion establecida")

    async def _on_ice(self, msg: dict) -> None:
        if not self._pc:
            return
        candidate = candidate_from_sdp(msg["candidate"])
        candidate.sdpMid = msg.get("sdpMid")
        candidate.sdpMLineIndex = msg.get("sdpMLineIndex")
        await self._pc.addIceCandidate(candidate)

    # ---------------------------------------------------------------- limpieza
    async def _teardown(self) -> None:
        if self._screen:
            self._screen.stop()
            self._screen = None
        if self._pc:
            await self._pc.close()
            self._pc = None
        self._token = None
        log.info("sesion cerrada; el agente sigue disponible para nuevas conexiones")

    def _print_credentials(self, agent_id: str, password: str) -> None:
        banner = (
            "\n" + "=" * 44 + "\n"
            "  ESTE EQUIPO ESTA LISTO PARA CONTROL REMOTO\n"
            + "=" * 44 + "\n"
            f"  ID:    {agent_id}\n"
            f"  CLAVE: {password}\n"
            + "=" * 44 + "\n"
            "  Comparte estos datos SOLO con quien confies.\n"
        )
        log.info("credenciales asignadas")
        print(banner)
