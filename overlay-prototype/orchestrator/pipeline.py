"""Event queue and processing hooks; providers are intentionally not configured."""
from __future__ import annotations

from queue import Queue
from typing import Any

from .bridge import OverlayBridge


class Pipeline:
    def __init__(self, bridge: OverlayBridge):
        self.bridge = bridge
        self.events: Queue[dict[str, Any]] = Queue()

    def submit(self, event: dict[str, Any]) -> None:
        self.events.put(event)

    def run_once(self) -> dict[str, Any]:
        event = self.events.get()
        # Connect capture/STT/LLM providers here; keep secrets in environment variables.
        return event

    def display_text(self, text: str) -> None:
        self.bridge.set_text(text)
