"""Local prototype defaults."""
from dataclasses import dataclass


@dataclass(frozen=True)
class OverlaySettings:
    width: int = 640
    height: int = 240
    x: int = 100
    y: int = 100
    hotkey_toggle: str = "CTRL+SHIFT+SPACE"
    capture_region: tuple[int, int, int, int] = (0, 0, 1280, 720)
    audio_enabled: bool = False
    llm_model: str = ""
