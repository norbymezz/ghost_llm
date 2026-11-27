from __future__ import annotations

import time

import pytesseract
from PIL import Image

from orchestrator.capture_types import CaptureFrame, OcrResult


class TesseractOcrEngine:
    """Motor OCR local basado en Tesseract 5."""

    def __init__(
        self,
        lang: str = "eng",
        psm: int = 6,
        timeout_s: float = 5.0,
    ) -> None:
        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

        self.lang = lang
        self.timeout_s = timeout_s
        self.config = (
            f"--oem 1 --psm {psm} "
            "-c preserve_interword_spaces=1 "
            "-c load_system_dawg=0 "
            "-c load_freq_dawg=0"
        )

    def recognize(self, frame: CaptureFrame) -> OcrResult:
        t0 = time.perf_counter()

        try:
            expected = frame.width * frame.height * 4

            if (
                frame.width <= 0
                or frame.height <= 0
                or frame.written != expected
                or len(frame.buffer) < expected
            ):
                raise ValueError("Buffer de captura inconsistente.")

            image = Image.frombytes(
                "RGBA",
                (frame.width, frame.height),
                frame.buffer[:expected],
                "raw",
                "BGRA",
            ).convert("RGB")

            text = pytesseract.image_to_string(
                image,
                lang=self.lang,
                config=self.config,
                timeout=self.timeout_s,
            )

            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            return OcrResult(
                text=text,
                elapsed_ms=elapsed_ms,
                error=None,
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            return OcrResult(
                text="",
                elapsed_ms=elapsed_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
