"""Smoke test; requires a built Windows DLL."""
import os
import pytest

from orchestrator.bridge import OverlayBridge


@pytest.mark.skipif(os.name != "nt", reason="Win32 DLL only")
def test_bridge_load_text_and_visibility():
    bridge = OverlayBridge()
    bridge.initialize()
    try:
        bridge.set_text("Prueba de texto")
        bridge.set_visible(False)
        bridge.set_visible(True)
    finally:
        bridge.shutdown()
