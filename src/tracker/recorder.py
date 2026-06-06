from __future__ import annotations

import time
from dataclasses import dataclass, field

from .app_context import get_active_app_context
from .config import TrackerConfig
from .events import Event, EventType
from .ocr import OCRProcessor
from .privacy import (
    is_sensitive_ocr_text,
    is_sensitive_window_title,
    redact_text,
    should_capture_shortcut,
)
from .screenshot import capture_screenshot
from .storage import SQLiteStorage


@dataclass(slots=True)
class RecorderState:
    running: bool = False
    paused: bool = False
    session_id: int | None = None
    pressed_modifiers: set[str] = field(default_factory=set)


class SessionRecorder:
    def __init__(self, config: TrackerConfig, storage: SQLiteStorage) -> None:
        self.config = config
        self.storage = storage
        self.ocr = OCRProcessor(enabled=config.ocr_enabled)
        self.state = RecorderState()
        self._keyboard_listener = None
        self._mouse_listener = None

    def run(self) -> int:
        self.config.ensure_directories()
        self.state.session_id = self.storage.create_session(
            local_only_mode=self.config.local_only_mode,
            screenshot_interval_seconds=self.config.screenshot_interval_seconds,
            ocr_enabled=self.config.ocr_enabled,
        )
        self.state.running = True

        app_name, window_title = get_active_app_context()
        self.storage.add_event(
            Event(
                session_id=self.state.session_id,
                event_type=EventType.SESSION_START,
                app_name=app_name,
                window_title=window_title,
                metadata={
                    "local_only_mode": self.config.local_only_mode,
                    "ocr_enabled": self.config.ocr_enabled,
                },
            )
        )

        self._start_input_listeners()

        try:
            next_screenshot = time.monotonic()
            while self.state.running:
                if self.state.paused:
                    time.sleep(0.1)
                    continue

                now = time.monotonic()
                if now >= next_screenshot:
                    self._record_snapshot()
                    next_screenshot = now + self.config.screenshot_interval_seconds
                time.sleep(0.05)
        except KeyboardInterrupt:
            self.state.running = False
        finally:
            self._shutdown()

        return int(self.state.session_id)

    def _start_input_listeners(self) -> None:
        from pynput import keyboard, mouse

        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._keyboard_listener.start()
        self._mouse_listener.start()

    def _shutdown(self) -> None:
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()

        if self.state.session_id is not None:
            app_name, window_title = get_active_app_context()
            self.storage.add_event(
                Event(
                    session_id=self.state.session_id,
                    event_type=EventType.SESSION_STOP,
                    app_name=app_name,
                    window_title=window_title,
                    metadata={"reason": "user_interrupt_or_stop"},
                )
            )
            self.storage.stop_session(self.state.session_id)

    def _record_snapshot(self) -> None:
        assert self.state.session_id is not None

        app_name, window_title = get_active_app_context()
        self.storage.add_event(
            Event(
                session_id=self.state.session_id,
                event_type=EventType.ACTIVE_WINDOW,
                app_name=app_name,
                window_title=window_title,
                metadata={},
            )
        )

        if is_sensitive_window_title(window_title):
            return

        image_path = capture_screenshot(self.config.screenshot_dir, self.state.session_id)
        self.storage.add_event(
            Event(
                session_id=self.state.session_id,
                event_type=EventType.SCREENSHOT,
                app_name=app_name,
                window_title=window_title,
                metadata={"path": str(image_path)},
            )
        )

        text = self.ocr.extract_text(image_path)
        if text and not is_sensitive_ocr_text(text):
            self.storage.add_event(
                Event(
                    session_id=self.state.session_id,
                    event_type=EventType.OCR_TEXT,
                    app_name=app_name,
                    window_title=window_title,
                    metadata={"text": redact_text(text, max_len=500)},
                )
            )

    def _normalize_key_name(self, key: object) -> str | None:
        key_str = str(key).replace("Key.", "").lower()
        if key_str.startswith("'") and key_str.endswith("'"):
            return key_str.strip("'")

        modifier_map = {
            "ctrl_l": "ctrl",
            "ctrl_r": "ctrl",
            "cmd": "cmd",
            "cmd_l": "cmd",
            "cmd_r": "cmd",
            "alt_l": "alt",
            "alt_r": "alt",
            "shift_l": "shift",
            "shift_r": "shift",
        }
        return modifier_map.get(key_str, key_str)

    def _on_key_press(self, key: object) -> None:
        key_name = self._normalize_key_name(key)
        if key_name in {"ctrl", "cmd", "alt", "shift"}:
            self.state.pressed_modifiers.add(key_name)
            return

        # Toggle pause/resume with Ctrl+Shift+P.
        if key_name == "p" and {"ctrl", "shift"}.issubset(self.state.pressed_modifiers):
            self.state.paused = not self.state.paused
            if self.state.session_id is not None:
                new_status = "paused" if self.state.paused else "running"
                self.storage.set_session_status(self.state.session_id, new_status)
            return

    def _on_key_release(self, key: object) -> None:
        key_name = self._normalize_key_name(key)
        if key_name in {"ctrl", "cmd", "alt", "shift"}:
            self.state.pressed_modifiers.discard(key_name)
            return

        if self.state.paused or not self.state.session_id:
            return

        if not should_capture_shortcut(self.state.pressed_modifiers, key_name):
            return

        app_name, window_title = get_active_app_context()
        if is_sensitive_window_title(window_title):
            return

        shortcut_parts = sorted(self.state.pressed_modifiers) + [key_name or "unknown"]
        shortcut = "+".join(shortcut_parts)

        self.storage.add_event(
            Event(
                session_id=self.state.session_id,
                event_type=EventType.KEYBOARD_SHORTCUT,
                app_name=app_name,
                window_title=window_title,
                metadata={"shortcut": shortcut},
            )
        )

    def _on_click(self, x: int, y: int, button: object, pressed: bool) -> None:
        if not pressed or self.state.paused or not self.state.session_id:
            return

        app_name, window_title = get_active_app_context()
        if is_sensitive_window_title(window_title):
            return

        self.storage.add_event(
            Event(
                session_id=self.state.session_id,
                event_type=EventType.MOUSE_CLICK,
                app_name=app_name,
                window_title=window_title,
                metadata={"x": x, "y": y, "button": str(button)},
            )
        )
