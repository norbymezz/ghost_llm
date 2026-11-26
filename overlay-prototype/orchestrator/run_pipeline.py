from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.bridge import OverlayConfig
from orchestrator.pipeline import OverlayPipeline, PipelineConfig
from orchestrator.debug_capture import make_png_capture_handler

def main() -> None:
    overlay_cfg = OverlayConfig(
        x=80,
        y=80,
        width=540,
        height=240,
        exclude_from_capture=True,
        topmost=True,
        click_through=False,
    )
    pipeline_cfg = PipelineConfig(
        capture_x=0,
        capture_y=0,
        capture_width=640,
        capture_height=360,
    )

    pipeline = OverlayPipeline(
        overlay_cfg=overlay_cfg,
        pipeline_cfg=pipeline_cfg,
        on_capture=make_png_capture_handler(output_dir="debug_captures", enabled=True),
    )
    pipeline.run()


if __name__ == "__main__":
    main()
