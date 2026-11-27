from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CaptureFrame:
    """Recorte de pantalla inmutable listo para ser consumido sin tocar el bridge."""

    x: int
    y: int
    width: int
    height: int
    buffer: bytes
    written: int
    timestamp: float  # Marca de time.perf_counter() para orden y medición en el proceso.


@dataclass(frozen=True)
class OcrResult:
    """Resultado de OCR. Convención: si error está presente, text debe ir vacío."""

    text: str
    elapsed_ms: float | None = None
    error: str | None = None


class FrameOcrEngine(Protocol):
    def recognize(self, frame: CaptureFrame) -> OcrResult:
        ...