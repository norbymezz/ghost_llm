from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable

from orchestrator.bridge import (
    OverlayBridge,
    OverlayConfig,
    OvHotkeyId,
    OvState,
)
from orchestrator.capture_types import CaptureFrame, FrameOcrEngine, OcrResult

# Modificadores y teclas virtuales Win32
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000

VK_F6 = 0x75
VK_F9 = 0x78
VK_F10 = 0x79
VK_UP = 0x26
VK_DOWN = 0x28
VK_LEFT = 0x25
VK_RIGHT = 0x27

VK_ADD = 0x6B
VK_SUBTRACT = 0x6D

VK_PRIOR = 0x21  # Page Up
VK_NEXT = 0x22   # Page Down

OVERLAY_MOVE_STEP = 10
OVERLAY_RESIZE_WIDTH_STEP = 40
OVERLAY_RESIZE_HEIGHT_STEP = 25

OVERLAY_MIN_WIDTH = 160
OVERLAY_MIN_HEIGHT = 80

OVERLAY_OPACITY_STEP = 26  # aproximadamente 10 %
OVERLAY_MIN_ALPHA = 26  # aproximadamente 10 % de opacidad

CaptureHandler = Callable[[int, int, int, int, bytearray, int], None]


@dataclass
class PipelineConfig:
    capture_x: int = 0
    capture_y: int = 0
    capture_width: int = 640
    capture_height: int = 360
    toggle_modifiers: int = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
    toggle_vk: int = VK_F6
    capture_modifiers: int = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
    capture_vk: int = VK_F9
    clear_modifiers: int = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
    clear_vk: int = VK_F10
    move_modifiers: int = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
    move_up_vk: int = VK_UP
    move_down_vk: int = VK_DOWN
    move_left_vk: int = VK_LEFT
    move_right_vk: int = VK_RIGHT

    resize_modifiers: int = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
    resize_increase_vk: int = VK_ADD
    resize_decrease_vk: int = VK_SUBTRACT

    opacity_modifiers: int = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
    opacity_increase_vk: int = VK_PRIOR
    opacity_decrease_vk: int = VK_NEXT

    poll_timeout_s: float = 0.05


class OverlayPipeline:
    def __init__(
        self,
        overlay_cfg: OverlayConfig | None = None,
        pipeline_cfg: PipelineConfig | None = None,
        on_capture: CaptureHandler | None = None,
        ocr_engine: FrameOcrEngine | None = None,
    ) -> None:
        self.overlay_cfg = overlay_cfg or OverlayConfig(
            x=80,
            y=80,
            width=540,
            height=240,
            exclude_from_capture=True,
            topmost=True,
            click_through=False,
        )
        self.cfg = pipeline_cfg or PipelineConfig()
        self.on_capture = on_capture
        self.ocr_engine = ocr_engine

        self._events: queue.Queue[int] = queue.Queue()
        self._stop_event = threading.Event()
        self._visible = True
        self._overlay_x = self.overlay_cfg.x
        self._overlay_y = self.overlay_cfg.y
        self._overlay_width = self.overlay_cfg.width
        self._overlay_height = self.overlay_cfg.height
        self._overlay_alpha = 255
        self._busy = False
        self._busy_lock = threading.Lock()
        self._worker: threading.Thread | None = None

        required_bytes = self.cfg.capture_width * self.cfg.capture_height * 4
        self._capture_buf = bytearray(required_bytes)

    def stop(self) -> None:
        self._stop_event.set()

    def _enqueue_hotkey(self, hotkey_id: int) -> None:
        if not self._stop_event.is_set():
            self._events.put_nowait(hotkey_id)

    def _wait_for_worker(self) -> None:
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join()

    def _run_capture_job(self, bridge: OverlayBridge) -> None:
        w = self.cfg.capture_width
        h = self.cfg.capture_height
        required = w * h * 4

        if len(self._capture_buf) < required:
            self._capture_buf = bytearray(required)

        try:
            if self._stop_event.is_set():
                return

            bridge.set_text(
                f"Capturando región ({self.cfg.capture_x}, {self.cfg.capture_y}, {w}x{h})...",
                OvState.STREAMING,
            )

            if self._stop_event.is_set():
                return

            t0 = time.perf_counter()
            written = bridge.capture_region(
                self.cfg.capture_x,
                self.cfg.capture_y,
                w,
                h,
                self._capture_buf,
            )
            capture_ts = time.perf_counter()
            elapsed_ms = (capture_ts - t0) * 1000.0

            if self._stop_event.is_set():
                return

            frame: CaptureFrame | None = None

            if self.ocr_engine is not None:
                frame = CaptureFrame(
                    x=self.cfg.capture_x,
                    y=self.cfg.capture_y,
                    width=w,
                    height=h,
                    buffer=bytes(memoryview(self._capture_buf)[:written]),
                    written=written,
                    timestamp=capture_ts,
                )

            if self._stop_event.is_set():
                return

            if self.on_capture is not None:
                self.on_capture(
                    self.cfg.capture_x,
                    self.cfg.capture_y,
                    w,
                    h,
                    self._capture_buf,
                    written,
                )

            if self._stop_event.is_set():
                return

            if self.ocr_engine is not None:
                assert frame is not None
                ocr_result: OcrResult = self.ocr_engine.recognize(frame)

                if self._stop_event.is_set():
                    return

                if ocr_result.error:
                    bridge.set_text(
                        f"OCR error: {ocr_result.error}",
                        OvState.IDLE,
                    )
                elif not ocr_result.text.strip():
                    bridge.set_text(
                        "OCR: sin texto detectado.",
                        OvState.IDLE,
                    )
                else:
                    bridge.set_text(ocr_result.text, OvState.IDLE)

                return

            bridge.set_text(
                f"Captura lista: {written} bytes en {elapsed_ms:.1f} ms.",
                OvState.IDLE,
            )

        except Exception as exc:
            if not self._stop_event.is_set():
                try:
                    bridge.set_text(f"Error de captura: {exc}", OvState.IDLE)
                except Exception:
                    pass
        finally:
            with self._busy_lock:
                self._busy = False

    def _handle_hotkey(self, bridge: OverlayBridge, hotkey_id: int) -> None:
        if self._stop_event.is_set():
            return

        if hotkey_id == OvHotkeyId.TOGGLE_VISIBILITY:
            self._visible = not self._visible
            bridge.set_visible(self._visible)

        elif hotkey_id == OvHotkeyId.CAPTURE_REGION:
            with self._busy_lock:
                if self._busy:
                    return
                self._busy = True
                worker = threading.Thread(
                    target=self._run_capture_job,
                    args=(bridge,),
                )
                self._worker = worker

            try:
                worker.start()
            except RuntimeError:
                with self._busy_lock:
                    self._busy = False
                    self._worker = None
                raise

        elif hotkey_id == OvHotkeyId.CLEAR:
            bridge.set_text("", OvState.IDLE)

        elif hotkey_id == OvHotkeyId.MOVE_UP:
            y = self._overlay_y - OVERLAY_MOVE_STEP
            bridge.set_position(self._overlay_x, y)
            self._overlay_y = y

        elif hotkey_id == OvHotkeyId.MOVE_DOWN:
            y = self._overlay_y + OVERLAY_MOVE_STEP
            bridge.set_position(self._overlay_x, y)
            self._overlay_y = y

        elif hotkey_id == OvHotkeyId.MOVE_LEFT:
            x = self._overlay_x - OVERLAY_MOVE_STEP
            bridge.set_position(x, self._overlay_y)
            self._overlay_x = x

        elif hotkey_id == OvHotkeyId.MOVE_RIGHT:
            x = self._overlay_x + OVERLAY_MOVE_STEP
            bridge.set_position(x, self._overlay_y)
            self._overlay_x = x
        
        elif hotkey_id == OvHotkeyId.RESIZE_INCREASE:
            width = self._overlay_width + OVERLAY_RESIZE_WIDTH_STEP
            height = self._overlay_height + OVERLAY_RESIZE_HEIGHT_STEP
            bridge.set_size(width, height)
            self._overlay_width = width
            self._overlay_height = height

        elif hotkey_id == OvHotkeyId.RESIZE_DECREASE:
            width = max(
                OVERLAY_MIN_WIDTH,
                self._overlay_width - OVERLAY_RESIZE_WIDTH_STEP,
            )
            height = max(
                OVERLAY_MIN_HEIGHT,
                self._overlay_height - OVERLAY_RESIZE_HEIGHT_STEP,
            )
            bridge.set_size(width, height)
            self._overlay_width = width
            self._overlay_height = height

        elif hotkey_id == OvHotkeyId.OPACITY_INCREASE:
            alpha = min(255, self._overlay_alpha + OVERLAY_OPACITY_STEP)
            bridge.set_opacity(alpha)
            self._overlay_alpha = alpha

        elif hotkey_id == OvHotkeyId.OPACITY_DECREASE:
            alpha = max(OVERLAY_MIN_ALPHA, self._overlay_alpha - OVERLAY_OPACITY_STEP)
            bridge.set_opacity(alpha)
            self._overlay_alpha = alpha

    def run(self) -> None:
        self._stop_event.clear()

        with OverlayBridge() as bridge:
            bridge.init(self.overlay_cfg)
            bridge.register_hotkey_callback(self._enqueue_hotkey)

            bridge.register_hotkey(
                OvHotkeyId.TOGGLE_VISIBILITY,
                self.cfg.toggle_modifiers,
                self.cfg.toggle_vk,
            )
            bridge.register_hotkey(
                OvHotkeyId.CAPTURE_REGION,
                self.cfg.capture_modifiers,
                self.cfg.capture_vk,
            )
            bridge.register_hotkey(
                OvHotkeyId.CLEAR,
                self.cfg.clear_modifiers,
                self.cfg.clear_vk,
            )
            bridge.register_hotkey(
                OvHotkeyId.MOVE_UP,
                self.cfg.move_modifiers,
                self.cfg.move_up_vk,
            )
            bridge.register_hotkey(
                OvHotkeyId.MOVE_DOWN,
                self.cfg.move_modifiers,
                self.cfg.move_down_vk,
            )
            bridge.register_hotkey(
                OvHotkeyId.MOVE_LEFT,
                self.cfg.move_modifiers,
                self.cfg.move_left_vk,
            )
            bridge.register_hotkey(
                OvHotkeyId.MOVE_RIGHT,
                self.cfg.move_modifiers,
                self.cfg.move_right_vk,
            )
            bridge.register_hotkey(
                OvHotkeyId.RESIZE_INCREASE,
                self.cfg.resize_modifiers,
                self.cfg.resize_increase_vk,
            )
            bridge.register_hotkey(
                OvHotkeyId.RESIZE_DECREASE,
                self.cfg.resize_modifiers,
                self.cfg.resize_decrease_vk,
            )
            bridge.register_hotkey(
                OvHotkeyId.OPACITY_INCREASE,
                self.cfg.opacity_modifiers,
                self.cfg.opacity_increase_vk,
            )
            bridge.register_hotkey(
                OvHotkeyId.OPACITY_DECREASE,
                self.cfg.opacity_modifiers,
                self.cfg.opacity_decrease_vk,
            )
            bridge.set_visible(self._visible)
            bridge.set_text(
                "Ctrl+Alt+F6: mostrar/ocultar | F9: capturar | F10: limpiar\n"
                "Flechas: mover | NumPad +/-: redimensionar | "
                "PageUp/Down: opacidad",
                OvState.IDLE,
            )

            try:
                while not self._stop_event.is_set():
                    try:
                        hk_id = self._events.get(timeout=self.cfg.poll_timeout_s)
                    except queue.Empty:
                        continue
                    self._handle_hotkey(bridge, hk_id)
            except KeyboardInterrupt:
                self._stop_event.set()
            finally:
                self._stop_event.set()
                self._wait_for_worker()
