from __future__ import annotations

from collections.abc import Iterable

from .events import Event, EventType


class PseudocodeGenerator:
    def generate(self, events: list[Event]) -> str:
        steps = self._build_steps(events)
        if not steps:
            return "1. No significant actions captured."
        return "\n".join(f"{idx}. {step}" for idx, step in enumerate(steps, start=1))

    def _build_steps(self, events: Iterable[Event]) -> list[str]:
        steps: list[str] = []
        last_window: str | None = None

        for event in events:
            if event.event_type == EventType.SESSION_START and event.app_name:
                steps.append(f"Opened {event.app_name}.")
                continue

            if event.event_type == EventType.ACTIVE_WINDOW and event.window_title:
                if event.window_title != last_window:
                    steps.append(f'Switched to window "{event.window_title}".')
                    last_window = event.window_title
                continue

            if event.event_type == EventType.MOUSE_CLICK:
                button = str(event.metadata.get("button", "mouse")).replace("Button.", "")
                if event.window_title:
                    steps.append(f"Clicked {button} in {event.window_title}.")
                else:
                    steps.append(f"Clicked {button}.")
                continue

            if event.event_type == EventType.KEYBOARD_SHORTCUT:
                combo = event.metadata.get("shortcut")
                if combo:
                    steps.append(f"Used shortcut {combo}.")
                continue

            if event.event_type == EventType.OCR_TEXT:
                text = str(event.metadata.get("text", "")).lower()
                if "chart" in text:
                    steps.append("Worked with chart-related content.")
                elif "table" in text:
                    steps.append("Worked with tabular data.")

        return steps
