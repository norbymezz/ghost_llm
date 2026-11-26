from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from orchestrator.bridge import (
    OverlayBridge,
    OverlayBridgeError,
    OverlayConfig,
    OvState,
    OvStatus,
)


class TestCaptureRegion(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ov = OverlayBridge()
        cls.ov.init(
            OverlayConfig(
                x=120,
                y=120,
                width=360,
                height=180,
                exclude_from_capture=True,
                topmost=True,
                click_through=False,
            )
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.ov.shutdown()

    def test_01_invalid_dimensions_and_empty_buffer(self) -> None:
        buf = bytearray(64)
        for bad_w, bad_h in [(0, 10), (-1, 10), (10, 0), (10, -5), (0, 0)]:
            with self.subTest(w=bad_w, h=bad_h):
                with self.assertRaises(ValueError):
                    self.ov.capture_region(0, 0, bad_w, bad_h, buf)

        with self.assertRaises(ValueError):
            self.ov.capture_region(0, 0, 10, 10, bytearray(0))

    def test_02_overflow_protection_large_dimensions(self) -> None:
        buf = bytearray(16)
        with self.assertRaises(OverlayBridgeError) as ctx:
            self.ov.capture_region(0, 0, 20000, 20000, buf)
        self.assertEqual(ctx.exception.status, OvStatus.ERR_INVALID_ARG)

    def test_03_buffer_too_small_returns_exact_error(self) -> None:
        w, h = 64, 64
        required = w * h * 4

        for size in (1, 16, required - 4, required - 1):
            with self.subTest(buffer_size=size):
                buf = bytearray([0xAA] * size)
                with self.assertRaises(OverlayBridgeError) as ctx:
                    self.ov.capture_region(0, 0, w, h, buf)
                self.assertEqual(ctx.exception.status, OvStatus.ERR_BUFFER_TOO_SMALL)
                # Verificar que no se modificó el buffer ante error de tamaño
                self.assertEqual(buf, bytearray([0xAA] * size))

    def test_04_exact_buffer_and_alpha_channel_opaque(self) -> None:
        w, h = 160, 90
        required = w * h * 4
        buf = bytearray(required)

        written = self.ov.capture_region(0, 0, w, h, buf)
        self.assertEqual(written, required)
        self.assertEqual(len(buf), required)

        alpha_slice = bytes(buf[3::4])
        self.assertEqual(len(alpha_slice), w * h)
        self.assertEqual(alpha_slice, b"\xff" * (w * h))

        bgr_only = bytearray(buf)
        del bgr_only[3::4]
        self.assertGreater(len(set(bgr_only)), 1, "La captura parece completamente plana/vacía")

        # Chequeo estructural básico: mitad superior y mitad inferior no son idénticas
        # (ayuda a detectar inversiones o desplazamientos groseros en la captura)
        half = (w * h * 4) // 2
        self.assertNotEqual(buf[:half], buf[half:], "Mitad superior e inferior idénticas")

    def test_05_oversized_buffer_preserves_trailing_sentinel(self) -> None:
        w, h = 80, 60
        required = w * h * 4
        sentinel = b"SENTINEL_TAIL_1234567890"
        buf = bytearray(required + len(sentinel))
        buf[required:] = sentinel

        written = self.ov.capture_region(10, 10, w, h, buf)
        self.assertEqual(written, required)
        self.assertEqual(bytes(buf[required:]), sentinel, "Se escribieron bytes fuera de required_bytes")

    def test_06_overlay_excluded_from_captured_region(self) -> None:
        x, y, w, h = 120, 120, 360, 180
        required = w * h * 4

        self.ov.set_visible(False)
        time.sleep(0.1)
        buf_without = bytearray(required)
        self.assertEqual(self.ov.capture_region(x, y, w, h, buf_without), required)

        self.ov.set_visible(True)
        self.ov.set_text("TEST EXCLUSION CAPTURE", OvState.STREAMING)
        time.sleep(0.15)

        buf_with = bytearray(required)
        self.assertEqual(self.ov.capture_region(x, y, w, h, buf_with), required)

        self.ov.set_visible(False)
        # Nota: sensible a cambios dinámicos en el escritorio (cursores, animaciones, reloj)
        # entre ambas tomas; útil en entorno estático o para inspección visual vía PNG.
        self.assertEqual(
            buf_without,
            buf_with,
            "La captura con overlay visible difirió de la captura sin overlay",
        )

    def test_07_repeated_captures_and_throughput(self) -> None:
        w, h = 320, 180
        required = w * h * 4
        buf = bytearray(required)
        iterations = 30

        t0 = time.perf_counter()
        for i in range(iterations):
            written = self.ov.capture_region(i * 4, i * 2, w, h, buf)
            self.assertEqual(written, required)
            self.assertEqual(bytes(buf[3::4]), b"\xff" * (w * h))
        elapsed = time.perf_counter() - t0

        avg_ms = (elapsed / iterations) * 1000.0
        print(f"\n[bench] {iterations} capturas ({w}x{h} BGRA): total={elapsed*1000:.1f} ms, promedio={avg_ms:.2f} ms/frame")
        self.assertLess(avg_ms, 250.0, "Latencia promedio por captura demasiado alta")

    def test_08_optional_png_export_if_pillow_available(self) -> None:
        try:
            from PIL import Image  # type: ignore
        except ImportError:
            self.skipTest("Pillow no instalado; se omite exportación visual PNG")

        w, h = 400, 225
        buf = bytearray(w * h * 4)
        written = self.ov.capture_region(0, 0, w, h, buf)
        self.assertEqual(written, w * h * 4)

        # BGRA -> RGBA para Pillow
        rgba = bytearray(len(buf))
        rgba[0::4] = buf[2::4]  # R <- B
        rgba[1::4] = buf[1::4]  # G <- G
        rgba[2::4] = buf[0::4]  # B <- R
        rgba[3::4] = buf[3::4]  # A <- A

        img = Image.frombytes("RGBA", (w, h), bytes(rgba), "raw", "RGBA", 0, 1)
        out_path = Path(tempfile.gettempdir()) / "ghost_llm_capture_test.png"
        img.save(out_path)
        self.assertTrue(out_path.exists() and out_path.stat().st_size > 0)
        print(f"\n[png] Captura guardada en: {out_path}")
        try:
            os.remove(out_path)
        except OSError:
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
