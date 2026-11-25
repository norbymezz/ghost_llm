from __future__ import annotations

import ctypes
import queue
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from orchestrator.bridge import OverlayBridge, OverlayConfig, OvHotkeyId, OvState

# Modificadores y teclas virtuales de Win32
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000

VK_F6 = 0x75
VK_F9 = 0x78
VK_F10 = 0x79


def main() -> None:
    event_queue: queue.Queue[int] = queue.Queue()
    visible = True

    def on_hotkey_native(hotkey_id: int) -> None:
        # Mantener liviano el callback: solo encolar el ID
        event_queue.put_nowait(hotkey_id)

    cfg = OverlayConfig(
        x=80,
        y=80,
        width=540,
        height=240,
        exclude_from_capture=True,
        topmost=True,
        click_through=False,
    )

    print("Iniciando overlay...")
    print("Atajos de prueba:")
    print("  Ctrl + Alt + F6  -> Mostrar / Ocultar overlay")
    print("  Ctrl + Alt + F9  -> Simular estado STREAMING + texto de prueba")
    print("  Ctrl + Alt + F10 -> Limpiar texto y volver a IDLE")
    print("  Ctrl + C en consola -> Salir\n")

    with OverlayBridge() as ov:
        ov.register_hotkey_callback(on_hotkey_native)
        ov.register_hotkey(
            OvHotkeyId.TOGGLE_VISIBILITY,
            MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
            VK_F6,
        )
        ov.register_hotkey(
            OvHotkeyId.CAPTURE_REGION,
            MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
            VK_F9,
        )
        ov.register_hotkey(
            OvHotkeyId.CLEAR,
            MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
            VK_F10,
        )

        ov.set_visible(True)
        ov.set_text("Listo. Probá Ctrl+Alt+F6, F9 o F10...", OvState.IDLE)

        try:
            while True:
                try:
                    hk_id = event_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                print(f"Hotkey recibido: {hk_id} ({OvHotkeyId(hk_id).name})")

                if hk_id == OvHotkeyId.TOGGLE_VISIBILITY:
                    visible = not visible
                    ov.set_visible(visible)
                elif hk_id == OvHotkeyId.CAPTURE_REGION:
                    ov.set_text(
                        "Atajo F9 detectado: aquí dispararemos captura + LLM.",
                        OvState.STREAMING,
                    )
                elif hk_id == OvHotkeyId.CLEAR:
                    ov.set_text("", OvState.IDLE)

        except KeyboardInterrupt:
            print("\nCerrando overlay y liberando hotkeys...")


if __name__ == "__main__":
    main()
