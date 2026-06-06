from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image


class OCRProcessor:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def extract_text(self, image_path: Path) -> str | None:
        if not self.enabled:
            return None
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
        except Exception:
            return None

        cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return cleaned or None
