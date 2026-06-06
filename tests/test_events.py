from tracker.events import Event, EventType


def test_event_creation_defaults() -> None:
    event = Event(session_id=1, event_type=EventType.MOUSE_CLICK)

    assert event.id is None
    assert event.session_id == 1
    assert event.event_type == EventType.MOUSE_CLICK
    assert isinstance(event.metadata, dict)
    assert event.iso_timestamp()
