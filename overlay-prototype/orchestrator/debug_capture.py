from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from PIL import Image


def bgra_to_rgba(bgra_buf: bytearray | bytes, width: int, height: int) -> bytes:
    expected = width * height * 4
    if len(bgra_buf) < expected:
        raise ValueError(
            f"Buffer insuficiente para {width}x{height} BGRA: "
            f"se esperaban {expected} bytes y hay {len(bgra_buf)}."
        )

    view = memoryview(bgra_buf)[:expected]
    rgba = bytearray(expected)
    rgba[0::4] = view[2::4]  # R <- B
    rgba[1::4] = view[1::4]  # G <- G
    rgba[2::4] = view[0::4]  # B <- R
    rgba[3::4] = view[3::4]  # A <- A
    return bytes(rgba)


def make_png_capture_handler(
    output_dir: str | Path = "debug_captures",
    enabled: bool = True,
) -> Callable[[int, int, int, int, bytearray, int], None]:
    out_path = Path(output_dir)

    def _on_capture(
        x: int,
        y: int,
        width: int,
        height: int,
        buf: bytearray,
        written: int,
    ) -> None:
        if not enabled:
            return
        expected = width * height * 4
        if written != expected:
            raise ValueError(
                f"Captura incompleta: se esperaban {expected} bytes "
                f"y se informaron {written}."
            )
        out_path.mkdir(parents=True, exist_ok=True)
        rgba_bytes = bgra_to_rgba(buf, width, height)
        image = Image.frombytes("RGBA", (width, height), rgba_bytes, "raw", "RGBA", 0, 1)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = out_path / f"cap_{stamp}_x{x}_y{y}_{width}x{height}_b{written}.png"
        image.save(filename)
        print(f"[debug_capture] Guardado: {filename}")

    return _on_capture
