"""ctypes wrapper for the native overlay DLL."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path


class OverlayConfig(ctypes.Structure):
    _fields_ = [("width", ctypes.c_int32), ("height", ctypes.c_int32),
                ("x", ctypes.c_int32), ("y", ctypes.c_int32)]


class OverlayBridge:
    def __init__(self, dll_path: str | os.PathLike[str] | None = None):
        path = Path(dll_path) if dll_path else Path(__file__).parents[1] / "native" / "build" / "Release" / "overlay.dll"
        self._dll = ctypes.CDLL(str(path))
        self._dll.overlay_initialize.argtypes = [ctypes.POINTER(OverlayConfig)]
        self._dll.overlay_initialize.restype = ctypes.c_int32
        self._dll.overlay_set_text.argtypes = [ctypes.c_char_p]
        self._dll.overlay_set_text.restype = ctypes.c_int32
        self._dll.overlay_set_visible.argtypes = [ctypes.c_int32]
        self._dll.overlay_set_visible.restype = ctypes.c_int32
        self._dll.overlay_shutdown.argtypes = []
        self._dll.overlay_shutdown.restype = ctypes.c_int32

    def initialize(self, width: int = 640, height: int = 240, x: int = 100, y: int = 100) -> None:
        config = OverlayConfig(width, height, x, y)
        self._check(self._dll.overlay_initialize(ctypes.byref(config)))

    def set_text(self, text: str) -> None:
        self._check(self._dll.overlay_set_text(text.encode("utf-8")))

    def set_visible(self, visible: bool) -> None:
        self._check(self._dll.overlay_set_visible(int(visible)))

    def shutdown(self) -> None:
        self._check(self._dll.overlay_shutdown())

    @staticmethod
    def _check(code: int) -> None:
        if code != 0:
            raise RuntimeError(f"overlay DLL returned error {code}")
