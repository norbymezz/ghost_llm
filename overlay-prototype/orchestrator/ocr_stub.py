from __future__ import annotations

import time

from orchestrator.capture_types import CaptureFrame, OcrResult


class StubOcrEngine:
    """Motor OCR de prueba para validar el flujo completo sin dependencias externas."""

    def __init__(
        self,
        sample_text: str = "Texto OCR de prueba",
        simulated_delay_s: float = 0.0,
        fail_every_n: int | None = None,
        empty_on_even: bool = False,
    ) -> None:
        if fail_every_n is not None and fail_every_n <= 0:
            raise ValueError("fail_every_n debe ser None o un entero positivo (>= 1).")

        self.sample_text = sample_text
        self.simulated_delay_s = simulated_delay_s
        self.fail_every_n = fail_every_n
        self.empty_on_even = empty_on_even
        self.calls = 0

    def recognize(self, frame: CaptureFrame) -> OcrResult:
        self.calls += 1
        t0 = time.perf_counter()

        if self.simulated_delay_s > 0:
            time.sleep(self.simulated_delay_s)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        expected = frame.width * frame.height * 4
        if len(frame.buffer) < expected or frame.written != expected:
            return OcrResult(
                text="",
                elapsed_ms=elapsed_ms,
                error=(
                    f"Frame inconsistente ({frame.width}x{frame.height}): "
                    f"written={frame.written}, len(buffer)={len(frame.buffer)}."
                ),
            )

        if self.fail_every_n is not None and self.calls % self.fail_every_n == 0:
            return OcrResult(
                text="",
                elapsed_ms=elapsed_ms,
                error=f"Fallo simulado en llamada #{self.calls}.",
            )

        if self.empty_on_even and self.calls % 2 == 0:
            return OcrResult(
                text="",
                elapsed_ms=elapsed_ms,
                error=None,
            )

        text = (
            f"{self.sample_text} "
            f"[#{self.calls} @ ({frame.x},{frame.y}) {frame.width}x{frame.height}]"
        )
        return OcrResult(
            text=text,
            elapsed_ms=elapsed_ms,
            error=None,
        )
