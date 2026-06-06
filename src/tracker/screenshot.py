from __future__ import annotations

from datetime import datetime
from pathlib import Path

import mss
from PIL import Image


def capture_screenshot(output_dir: Path, session_id: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    image_path = output_dir / f"session_{session_id}_{stamp}.png"

    with mss.mss() as sct:
        monitor = sct.monitors[0]
        shot = sct.grab(monitor)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        image.save(image_path)

    return image_path
