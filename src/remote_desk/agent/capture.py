"""Captura de pantalla como pista de video WebRTC.

Usa `mss` (muy rapido) para capturar el monitor y lo entrega a aiortc como
`VideoFrame`. aiortc se encarga de codificar (VP8/H264) y cifrar (SRTP).
"""

from __future__ import annotations

import asyncio

import mss
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame

from remote_desk.common.logging import setup_logging

log = setup_logging("agent.capture")


class ScreenTrack(VideoStreamTrack):
    """Pista de video que emite capturas del monitor primario.

    El ritmo (fps) y los timestamps los gestiona `next_timestamp()` de la clase
    base de aiortc; nosotros solo aportamos cada frame ya convertido a RGB.
    """

    def __init__(self, monitor_index: int = 1) -> None:
        super().__init__()
        self._sct = mss.mss()
        # monitor 0 = todos combinados; 1 = primario.
        self._monitor = self._sct.monitors[monitor_index]
        self.width = self._monitor["width"]
        self.height = self._monitor["height"]
        log.info("capturando monitor %sx%s", self.width, self.height)

    async def recv(self) -> VideoFrame:
        # Deja que la clase base regule el ritmo y genere el timestamp.
        pts, time_base = await self.next_timestamp()

        # mss es sincrono; lo sacamos del event loop para no bloquearlo.
        raw = await asyncio.get_event_loop().run_in_executor(None, self._grab)

        frame = VideoFrame.from_ndarray(raw, format="rgb24")
        frame.pts = pts
        frame.time_base = time_base
        return frame

    def _grab(self) -> np.ndarray:
        shot = self._sct.grab(self._monitor)
        # mss entrega BGRA; convertimos a RGB contiguo.
        arr = np.asarray(shot, dtype=np.uint8)  # (h, w, 4) BGRA
        return np.ascontiguousarray(arr[:, :, 2::-1])  # -> RGB

    def stop(self) -> None:  # type: ignore[override]
        super().stop()
        try:
            self._sct.close()
        except Exception:  # noqa: BLE001
            pass
