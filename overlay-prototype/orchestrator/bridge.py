from __future__ import annotations

import ctypes
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Callable, Optional


class OvStatus(IntEnum):
    OK = 0
    ERR_INVALID_ARG = -1
    ERR_INIT_FAILED = -2
    ERR_NOT_INITIALIZED = -3
    ERR_BUFFER_TOO_SMALL = -4
    ERR_CAPTURE_FAILED = -5


class OvState(IntEnum):
    IDLE = 0
    CAPTURING = 1
    THINKING = 2
    STREAMING = 3
    ERROR = 4


class OvHotkeyId(IntEnum):
    TOGGLE_VISIBILITY = 1
    CAPTURE_REGION = 2
    TOGGLE_AUDIO = 3
    CLEAR = 4


class _OvConfigStruct(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("exclude_from_capture", ctypes.c_int),
        ("topmost", ctypes.c_int),
        ("click_through", ctypes.c_int),
    ]


_HOTKEY_CALLBACK_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_void_p)


@dataclass
class OverlayConfig:
    x: int = 80
    y: int = 80
    width: int = 520
    height: int = 240
    exclude_from_capture: bool = True
    topmost: bool = True
    click_through: bool = False

    def to_c_struct(self) -> _OvConfigStruct:
        return _OvConfigStruct(
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            exclude_from_capture=1 if self.exclude_from_capture else 0,
            topmost=1 if self.topmost else 0,
            click_through=1 if self.click_through else 0,
        )


class OverlayBridgeError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"{message} (status={status})")


def default_dll_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [
        repo_root / "native" / "build" / "Release" / "overlay.dll",
        repo_root / "native" / "build" / "overlay.dll",
        repo_root / "native" / "build" / "Debug" / "overlay.dll",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


class OverlayBridge:
    def __init__(self, dll_path: Optional[Path | str] = None) -> None:
        resolved = Path(dll_path) if dll_path else default_dll_path()
        if not resolved.exists():
            raise FileNotFoundError(f"No se encontró overlay.dll en: {resolved}")

        self._lib = ctypes.CDLL(str(resolved))
        self._configure_signatures()

        self._initialized = False
        self._user_callback: Optional[Callable[[int], None]] = None
        # Mantener referencia viva para evitar que ctypes/GC recolecte el callback nativo
        self._native_callback_ref: Optional[_HOTKEY_CALLBACK_TYPE] = None

    def _configure_signatures(self) -> None:
        self._lib.ov_init.argtypes = [ctypes.POINTER(_OvConfigStruct)]
        self._lib.ov_init.restype = ctypes.c_int

        self._lib.ov_shutdown.argtypes = []
        self._lib.ov_shutdown.restype = None

        self._lib.ov_set_visible.argtypes = [ctypes.c_int]
        self._lib.ov_set_visible.restype = ctypes.c_int

        self._lib.ov_set_text.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self._lib.ov_set_text.restype = ctypes.c_int

        self._lib.ov_register_hotkey_callback.argtypes = [_HOTKEY_CALLBACK_TYPE, ctypes.c_void_p]
        self._lib.ov_register_hotkey_callback.restype = ctypes.c_int

        self._lib.ov_register_hotkey.argtypes = [ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
        self._lib.ov_register_hotkey.restype = ctypes.c_int

        self._lib.ov_unregister_hotkey.argtypes = [ctypes.c_int]
        self._lib.ov_unregister_hotkey.restype = ctypes.c_int
        self._lib.ov_get_last_win32_error.argtypes = []
        self._lib.ov_get_last_win32_error.restype = ctypes.c_int

        self._lib.ov_capture_region.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ]
        self._lib.ov_capture_region.restype = ctypes.c_int

    def _check(self, status: int, action: str) -> None:
        if status != OvStatus.OK:
            raise OverlayBridgeError(status, f"Falló {action}")

    def init(self, config: Optional[OverlayConfig] = None) -> None:
        if self._initialized:
            return
        cfg = config or OverlayConfig()
        c_cfg = cfg.to_c_struct()
        status = self._lib.ov_init(ctypes.byref(c_cfg))
        self._check(status, "ov_init")
        self._initialized = True

    def shutdown(self) -> None:
        if not self._initialized:
            return
        try:
            self._lib.ov_shutdown()
        finally:
            self._initialized = False
            self._native_callback_ref = None

    def set_visible(self, visible: bool) -> None:
        status = self._lib.ov_set_visible(1 if visible else 0)
        self._check(status, "ov_set_visible")

    def set_text(self, text: str, state: OvState | int = OvState.IDLE) -> None:
        encoded = text.encode("utf-8", errors="replace")
        status = self._lib.ov_set_text(encoded, int(state))
        self._check(status, "ov_set_text")

    def register_hotkey_callback(self, callback: Callable[[int], None]) -> None:
        self._user_callback = callback

        def _trampoline(hotkey_id: int, _user_data: int) -> None:
            if self._user_callback is not None:
                self._user_callback(hotkey_id)

        self._native_callback_ref = _HOTKEY_CALLBACK_TYPE(_trampoline)
        status = self._lib.ov_register_hotkey_callback(self._native_callback_ref, None)
        self._check(status, "ov_register_hotkey_callback")

    def register_hotkey(self, hotkey_id: OvHotkeyId | int, modifiers: int, virtual_key: int) -> None:
        status = self._lib.ov_register_hotkey(int(hotkey_id), int(modifiers), int(virtual_key))

        if status != OvStatus.OK:
            win_error = self._lib.ov_get_last_win32_error()
            raise OverlayBridgeError(
                status,
                f"Falló ov_register_hotkey (Win32 error={win_error})"
            )

    def unregister_hotkey(self, hotkey_id: OvHotkeyId | int) -> None:
        status = self._lib.ov_unregister_hotkey(int(hotkey_id))
        self._check(status, "ov_unregister_hotkey")

    def capture_region(self, x: int, y: int, width: int, height: int, buffer: bytearray) -> int:
        if width <= 0 or height <= 0:
            raise ValueError("width y height deben ser mayores que cero")
        if len(buffer) <= 0:
            raise ValueError("buffer no puede estar vacío")

        c_buf = (ctypes.c_ubyte * len(buffer)).from_buffer(buffer)
        written = ctypes.c_int(0)
        status = self._lib.ov_capture_region(
            x,
            y,
            width,
            height,
            c_buf,
            len(buffer),
            ctypes.byref(written),
        )
        self._check(status, "ov_capture_region")
        return int(written.value)

    def __enter__(self) -> OverlayBridge:
        self.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.shutdown()


if __name__ == "__main__":
    import time

    with OverlayBridge() as ov:
        ov.set_visible(True)
        ov.set_text("Probando overlay excluido de captura...", OvState.STREAMING)
        time.sleep(5)
