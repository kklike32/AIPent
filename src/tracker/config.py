from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TrackerConfig:
    db_path: Path = Path("data/tracker.sqlite3")
    screenshot_dir: Path = Path("data/screenshots")
    export_dir: Path = Path("data/exports")
    screenshot_interval_seconds: int = 5
    ocr_enabled: bool = True
    local_only_mode: bool = True

    def ensure_directories(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
