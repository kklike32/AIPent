from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from .config import TrackerConfig


class AudioRecorder:
    def __init__(self, config: TrackerConfig) -> None:
        self.config = config
        self._process: subprocess.Popen[bytes] | None = None
        self.path: Path | None = None

    def start(self, session_id: str) -> Path | None:
        if not self.config.enable_audio_capture:
            return None
        self.config.audio_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        self.path = self.config.audio_dir / f"session_{session_id}_{stamp}.wav"
        command = [
            self.config.ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "avfoundation",
            "-i",
            self.config.audio_input_device,
            "-ac",
            "1",
            "-ar",
            str(self.config.audio_sample_rate),
            str(self.path),
        ]
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            self.path = None
            return None
        return self.path

    def stop(self) -> Path | None:
        if self._process is None:
            return self.path
        process = self._process
        self._process = None
        try:
            if process.stdin:
                process.stdin.write(b"q")
                process.stdin.flush()
            process.wait(timeout=5)
        except (BrokenPipeError, subprocess.TimeoutExpired):
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        return self.path
