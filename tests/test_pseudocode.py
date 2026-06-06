from datetime import datetime, timezone

from tracker.events import Event, EventType
from tracker.pseudocode import PseudocodeGenerator
from tracker.suggestions import SuggestionEngine


def test_pseudocode_generation_from_events() -> None:
    now = datetime.now(timezone.utc)
    events = [
        Event(
            session_id=1,
            event_type=EventType.SESSION_START,
            timestamp=now,
            app_name="Microsoft Excel",
        ),
        Event(
            session_id=1,
            event_type=EventType.ACTIVE_WINDOW,
            timestamp=now,
            window_title="Budget Workbook",
        ),
        Event(
            session_id=1,
            event_type=EventType.MOUSE_CLICK,
            timestamp=now,
            window_title="Budget Workbook",
            metadata={"button": "left"},
        ),
        Event(
            session_id=1,
            event_type=EventType.KEYBOARD_SHORTCUT,
            timestamp=now,
            metadata={"shortcut": "cmd+c"},
        ),
    ]

    pseudocode = PseudocodeGenerator().generate(events)

    assert "Opened Microsoft Excel." in pseudocode
    assert 'Switched to window "Budget Workbook".' in pseudocode
    assert "Used shortcut cmd+c." in pseudocode


def test_suggestions_generation_from_events() -> None:
    now = datetime.now(timezone.utc)
    events = [
        Event(session_id=1, event_type=EventType.MOUSE_CLICK, timestamp=now)
        for _ in range(12)
    ]
    events.append(
        Event(
            session_id=1,
            event_type=EventType.OCR_TEXT,
            timestamp=now,
            metadata={"text": "created chart from table"},
        )
    )

    pseudocode = "1. Clicked left."
    suggestions = SuggestionEngine().suggest(events, pseudocode)

    assert any("repetitive" in text.lower() for text in suggestions)
    assert any("chart" in text.lower() or "tabular" in text.lower() for text in suggestions)
