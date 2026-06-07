from uuid import UUID

from tracker.events import Event, EventType


def test_event_creation_defaults() -> None:
    event = Event(session_id="session-1", event_type=EventType.MOUSE_CLICK)

    UUID(event.id)
    assert event.session_id == "session-1"
    assert event.event_type == EventType.MOUSE_CLICK
    assert isinstance(event.metadata, dict)
    assert event.timestamp.isoformat()


def test_audio_recording_event_type_is_local_raw_data() -> None:
    event = Event(
        session_id="session-1",
        event_type=EventType.AUDIO_RECORDING,
        metadata={"path": "data/audio/session.wav"},
    )

    assert event.event_type == EventType.AUDIO_RECORDING
    assert event.metadata["path"].endswith(".wav")
