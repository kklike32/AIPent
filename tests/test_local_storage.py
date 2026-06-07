from datetime import datetime, timedelta, timezone
from pathlib import Path

from tracker.events import ChunkSummary, Event, EventType, FinalPseudocode, ScreenshotRecord, Session
from tracker.workflows import build_workflow_artifacts
from tracker.storage.local_sqlite import LocalSQLiteRepository


def test_local_sqlite_summary_roundtrip(tmp_path: Path) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    session = repository.create_session(Session(session_name="test", sync_enabled=False))

    repository.save_event(
        Event(
            session_id=session.id,
            event_type=EventType.KEYBOARD_SHORTCUT,
            metadata={"shortcut": "ctrl+s"},
        )
    )
    repository.save_chunk_summary(
        ChunkSummary(
            session_id=session.id,
            chunk_index=0,
            started_at="2026-01-01T00:00:00+00:00",
            ended_at="2026-01-01T00:00:06+00:00",
            summary="Edited a document.",
            observed_apps=["Word"],
            confidence="high",
        )
    )
    repository.save_final_pseudocode(
        FinalPseudocode(
            session_id=session.id,
            pseudocode=["Step 1. Edit the document."],
            plain_text="1. Edit the document.",
            suggestions=["Automate the template."],
        )
    )

    loaded_session = repository.get_session(session.id)
    events = repository.get_events(session.id)
    summaries = repository.get_chunk_summaries(session.id)
    final = repository.get_final_pseudocode(session.id)

    assert loaded_session is not None
    assert loaded_session.id == session.id
    assert len(events) == 1
    assert len(summaries) == 1
    assert summaries[0].observed_apps == ["Word"]
    assert final is not None
    assert final.pseudocode == ["Step 1. Edit the document."]


def test_local_sqlite_unsynced_summary_bookkeeping(tmp_path: Path) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    session = repository.create_session(Session(sync_enabled=True))
    summary = repository.save_chunk_summary(
        ChunkSummary(
            session_id=session.id,
            chunk_index=1,
            started_at="2026-01-01T00:00:06+00:00",
            ended_at="2026-01-01T00:00:12+00:00",
            summary="Reviewed a dashboard.",
            observed_apps=["Chrome"],
            confidence="medium",
        )
    )
    final = repository.save_final_pseudocode(
        FinalPseudocode(
            session_id=session.id,
            pseudocode=["Step 1. Review the dashboard."],
            plain_text="1. Review the dashboard.",
            suggestions=["Save the filtered view."],
        )
    )

    assert len(repository.list_unsynced_chunk_summaries(session.id)) == 1
    assert len(repository.list_unsynced_final_pseudocode(session.id)) == 1

    repository.mark_chunk_summary_synced(summary.id, "remote-summary")
    repository.mark_final_pseudocode_synced(final.id, "remote-final")

    assert repository.list_unsynced_chunk_summaries(session.id) == []
    assert repository.list_unsynced_final_pseudocode(session.id) == []


def test_local_sqlite_workflow_artifact_roundtrip(tmp_path: Path) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    session = repository.create_session(Session(sync_enabled=True))
    summary = repository.save_chunk_summary(
        ChunkSummary(
            session_id=session.id,
            chunk_index=1,
            started_at="2026-01-01T00:00:06+00:00",
            ended_at="2026-01-01T00:00:12+00:00",
            summary="Opened a spreadsheet, created a chart, and exported a report.",
            observed_apps=["Excel"],
            confidence="high",
        )
    )
    final = repository.save_final_pseudocode(
        FinalPseudocode(
            session_id=session.id,
            pseudocode=[
                "Step 1. Open the spreadsheet table.",
                "Step 2. Create the chart and export the report.",
            ],
            plain_text="1. Open the spreadsheet table.\n2. Create the chart and export the report.",
            suggestions=["Create a reusable workflow template and draft a Python automation plan."],
        )
    )

    artifacts = build_workflow_artifacts(final, [summary])
    insight = repository.save_workflow_insight(artifacts.insight)
    template = repository.save_workflow_template(artifacts.template)
    search_record = repository.save_workflow_search_index(artifacts.search_index)
    draft = repository.save_agent_handoff_draft(artifacts.handoff_draft)

    assert repository.get_workflow_insight(session.id) is not None
    assert repository.get_workflow_template(template.id) is not None
    assert repository.get_agent_handoff_draft(session.id) is not None
    assert repository.get_workflow_search_index_record(session.id) is not None

    repository.mark_workflow_insight_synced(insight.id, "remote-insight")
    repository.mark_workflow_template_synced(template.id, "remote-template")
    repository.mark_workflow_search_index_record_synced(search_record.id, "remote-search")
    repository.mark_agent_handoff_draft_synced(draft.id, "remote-draft")

    assert repository.list_unsynced_workflow_insights(session.id) == []
    assert repository.list_unsynced_workflow_templates(session.id) == []
    assert repository.list_unsynced_workflow_search_index_records(session.id) == []
    assert repository.list_unsynced_agent_handoff_drafts(session.id) == []


def test_local_sqlite_purges_expired_raw_data(tmp_path: Path) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    session = repository.create_session(Session(sync_enabled=False))
    old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    screenshot_path = tmp_path / "old_frame.png"
    screenshot_path.write_bytes(b"png")
    audio_path = tmp_path / "old_audio.wav"
    audio_path.write_bytes(b"wav")

    repository.save_event(
        Event(
            session_id=session.id,
            event_type=EventType.MOUSE_CLICK,
            timestamp=old_time,
            metadata={"x": 1, "y": 2, "button": "left"},
        )
    )
    repository.save_event(
        Event(
            session_id=session.id,
            event_type=EventType.SESSION_START,
            timestamp=old_time,
            metadata={},
        )
    )
    repository.save_event(
        Event(
            session_id=session.id,
            event_type=EventType.AUDIO_RECORDING,
            timestamp=old_time,
            metadata={"path": str(audio_path), "status": "stopped"},
        )
    )
    repository.save_screenshot(
        ScreenshotRecord(
            session_id=session.id,
            local_path=str(screenshot_path),
            captured_at=old_time,
        )
    )

    result = repository.purge_expired_raw_data(
        session.id,
        datetime.now(timezone.utc) - timedelta(minutes=5),
    )

    assert result["screenshots_deleted"] == 1
    assert result["event_rows_deleted"] == 2
    assert result["screenshot_files_deleted"] == 2
    assert screenshot_path.exists() is False
    assert audio_path.exists() is False
    remaining_events = repository.get_events(session.id)
    assert len(remaining_events) == 1
    assert remaining_events[0].event_type == EventType.SESSION_START
