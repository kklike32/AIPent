from pathlib import Path

from tracker.events import Event, EventType
from tracker.storage import SQLiteStorage


def test_sqlite_storage_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "tracker.sqlite3"
    storage = SQLiteStorage(db_path)

    session_id = storage.create_session(
        local_only_mode=True,
        screenshot_interval_seconds=5,
        ocr_enabled=True,
    )

    storage.add_event(
        Event(
            session_id=session_id,
            event_type=EventType.KEYBOARD_SHORTCUT,
            metadata={"shortcut": "ctrl+c"},
        )
    )

    events = storage.get_events(session_id)
    assert len(events) == 1
    assert events[0].event_type == EventType.KEYBOARD_SHORTCUT
    assert events[0].metadata["shortcut"] == "ctrl+c"

    storage.stop_session(session_id)
