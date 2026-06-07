from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import requests

from tracker.chunker import ActivityChunker
from tracker.config import TrackerConfig
from tracker.events import (
    AgentHandoffDraft,
    Event,
    EventType,
    FinalPseudocode,
    ScreenshotRecord,
    Session,
    WorkflowInsight,
    WorkflowSearchIndexRecord,
    WorkflowTemplate,
)
from tracker.llm.mock import MockLLMClient
from tracker.recorder import SessionRecorder
from tracker.storage.local_sqlite import LocalSQLiteRepository


class _DummyClient:
    def __init__(self) -> None:
        self.summary_payloads = []
        self.final_payloads = []
        self.insight_payloads = []
        self.template_payloads = []
        self.handoff_payloads = []
        self.search_payloads = []

    def create_session(self, payload: dict) -> dict:
        return {"id": payload["id"]}

    def upload_chunk_summary(self, payload: dict) -> dict:
        self.summary_payloads.append(payload)
        return {"id": payload["id"]}

    def upload_final_pseudocode(self, payload: dict) -> dict:
        self.final_payloads.append(payload)
        return {"id": payload["id"]}

    def upload_workflow_insight(self, payload: dict) -> dict:
        self.insight_payloads.append(payload)
        return {"id": payload["id"]}

    def upload_workflow_template(self, payload: dict) -> dict:
        self.template_payloads.append(payload)
        return {"id": payload["id"]}

    def upload_agent_handoff_draft(self, payload: dict) -> dict:
        self.handoff_payloads.append(payload)
        return {"id": payload["id"]}

    def upload_search_index_record(self, payload: dict) -> dict:
        self.search_payloads.append(payload)
        return {"id": payload["id"]}


def test_recorder_generates_local_raw_data_and_remote_summaries_only(tmp_path) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    config = TrackerConfig(
        db_path=tmp_path / "local_tracker.db",
        screenshot_dir=tmp_path / "screenshots",
        export_dir=tmp_path / "exports",
        enable_cloud_sync=True,
        llm_provider="mock",
    )
    dummy_client = _DummyClient()
    recorder = SessionRecorder(config, repository, MockLLMClient(), dummy_client)

    session = repository.create_session(Session(id="session-1", sync_enabled=True))
    recorder.state.session_id = session.id
    now = datetime.now(timezone.utc)
    recorder._chunker = ActivityChunker(session.id, now_provider=lambda: now)

    event = repository.save_event(
        Event(
            session_id=session.id,
            event_type=EventType.ACTIVE_WINDOW,
            app_name="Chrome",
            window_title="Docs",
            timestamp=now,
        )
    )
    recorder._chunker.add_event(event)
    screenshot = repository.save_screenshot(
        ScreenshotRecord(
            session_id=session.id,
            local_path=str(tmp_path / "frame.png"),
            captured_at=now,
            ocr_text="Visible document heading",
        )
    )
    recorder._chunker.mark_screenshot_captured(screenshot, now)
    ocr_event = repository.save_event(
        Event(
            session_id=session.id,
            event_type=EventType.OCR_TEXT,
            metadata={"text": "Visible document heading"},
            timestamp=now,
        )
    )
    recorder._chunker.add_event(ocr_event)

    recorder._process_due_chunk(now + timedelta(seconds=6))
    recorder._wait_for_pending_summaries()
    summaries = repository.get_chunk_summaries(session.id)
    recorder._upload_chunk_summary(summaries[0])
    final = repository.save_final_pseudocode(
        FinalPseudocode(
            session_id=session.id,
            pseudocode=["Step 1. Review Docs in Chrome."],
            plain_text="1. Review Docs in Chrome.",
            suggestions=["Save the recurring workflow."],
        )
    )
    recorder._upload_final_pseudocode(final)

    assert repository.get_events(session.id)
    assert repository.get_screenshots(session.id)
    assert summaries
    assert dummy_client.summary_payloads
    assert dummy_client.final_payloads
    assert "summary" in dummy_client.summary_payloads[0]
    assert "pseudocode" not in dummy_client.summary_payloads[0]
    assert "pseudocode" in dummy_client.final_payloads[0]
    assert "ocr_text" not in dummy_client.final_payloads[0]
    assert "screenshots" not in dummy_client.final_payloads[0]


def test_recorder_purges_expired_raw_data_after_summary(tmp_path) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    config = TrackerConfig(
        db_path=tmp_path / "local_tracker.db",
        screenshot_dir=tmp_path / "screenshots",
        export_dir=tmp_path / "exports",
        enable_cloud_sync=False,
        llm_provider="mock",
        raw_data_ttl_seconds=300,
    )
    recorder = SessionRecorder(config, repository, MockLLMClient(), None)

    session = repository.create_session(Session(id="session-ttl", sync_enabled=False))
    recorder.state.session_id = session.id
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(minutes=10)
    recorder._chunker = ActivityChunker(session.id, now_provider=lambda: now)

    old_screenshot_path = tmp_path / "old_frame.png"
    old_screenshot_path.write_bytes(b"png")

    repository.save_event(
        Event(
            session_id=session.id,
            event_type=EventType.MOUSE_CLICK,
            timestamp=old_time,
            metadata={"x": 10, "y": 20, "button": "left"},
        )
    )
    repository.save_screenshot(
        ScreenshotRecord(
            session_id=session.id,
            local_path=str(old_screenshot_path),
            captured_at=old_time,
        )
    )

    event = repository.save_event(
        Event(
            session_id=session.id,
            event_type=EventType.ACTIVE_WINDOW,
            app_name="Chrome",
            window_title="Docs",
            timestamp=now,
        )
    )
    recorder._chunker.add_event(event)
    screenshot = repository.save_screenshot(
        ScreenshotRecord(
            session_id=session.id,
            local_path=str(tmp_path / "fresh_frame.png"),
            captured_at=now,
            ocr_text="Visible document heading",
        )
    )
    recorder._chunker.mark_screenshot_captured(screenshot, now)

    recorder._process_due_chunk(now + timedelta(seconds=6))
    recorder._wait_for_pending_summaries()

    assert repository.get_chunk_summaries(session.id)
    assert old_screenshot_path.exists() is False
    remaining_events = repository.get_events(session.id)
    assert all(event.event_type != EventType.MOUSE_CLICK for event in remaining_events)


def test_recorder_emits_chunk_and_sync_events(tmp_path) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    config = TrackerConfig(
        db_path=tmp_path / "local_tracker.db",
        screenshot_dir=tmp_path / "screenshots",
        export_dir=tmp_path / "exports",
        enable_cloud_sync=True,
        llm_provider="mock",
    )
    emitted: list[dict] = []
    recorder = SessionRecorder(
        config,
        repository,
        MockLLMClient(),
        _DummyClient(),
        event_sink=emitted.append,
    )

    session = repository.create_session(Session(id="session-events", sync_enabled=True))
    recorder.state.session_id = session.id
    now = datetime.now(timezone.utc)
    recorder._chunker = ActivityChunker(session.id, now_provider=lambda: now)

    event = repository.save_event(
        Event(
            session_id=session.id,
            event_type=EventType.ACTIVE_WINDOW,
            app_name="Excel",
            window_title="Quarterly report",
            timestamp=now,
        )
    )
    recorder.state.event_count += 1
    recorder._chunker.add_event(event)
    screenshot = repository.save_screenshot(
        ScreenshotRecord(
            session_id=session.id,
            local_path=str(tmp_path / "frame.png"),
            captured_at=now,
        )
    )
    recorder.state.screenshot_count += 1
    recorder._chunker.mark_screenshot_captured(screenshot, now)

    recorder._process_due_chunk(now + timedelta(seconds=6))
    recorder._wait_for_pending_summaries()

    event_types = [event["type"] for event in emitted]
    assert event_types == [
        "chunk_started",
        "gemini_started",
        "chunk_summary_created",
        "insforge_sync_started",
        "insforge_sync_complete",
    ]
    assert emitted[0]["chunk_index"] == 0
    assert emitted[2]["observed_apps"] == ["Excel"]


def test_recorder_pause_resume_and_shutdown_emit_ui_events(tmp_path, monkeypatch) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    config = TrackerConfig(
        db_path=tmp_path / "local_tracker.db",
        screenshot_dir=tmp_path / "screenshots",
        export_dir=tmp_path / "exports",
        enable_cloud_sync=False,
        llm_provider="mock",
    )
    emitted: list[dict] = []
    recorder = SessionRecorder(config, repository, MockLLMClient(), None, event_sink=emitted.append)

    monkeypatch.setattr("tracker.recorder.get_active_app_context", lambda: ("Chrome", "Docs"))
    monkeypatch.setattr(
        recorder.llm_client,
        "generate_final_pseudocode_with_audio",
        lambda _summaries, _audio_path: FinalPseudocode(
            session_id="session-ui",
            pseudocode=["Step 1. Open Docs."],
            plain_text="1. Open Docs.",
            suggestions=["Turn this into a template."],
        ),
    )
    monkeypatch.setattr(
        "tracker.recorder.build_workflow_artifacts",
        lambda final, _summaries, **_kwargs: SimpleNamespace(
            insight=WorkflowInsight(
                session_id=final.session_id,
                summary="A browser workflow.",
                main_apps=["Chrome"],
                detected_task_type="browser_admin_workflow",
                tags=["browser"],
                automation_score=84,
                automation_reason="Highly repetitive steps.",
                recommended_next_action="Create a reusable workflow template.",
            ),
            template=WorkflowTemplate(
                session_id=final.session_id,
                title="Open Docs",
                description="Reusable browser workflow",
                category="browser_admin_workflow",
                tags=["browser"],
                pseudocode=final.pseudocode,
                plain_text=final.plain_text,
            ),
            search_index=WorkflowSearchIndexRecord(
                session_id=final.session_id,
                template_id=None,
                searchable_text="open docs browser",
                tags=["browser"],
            ),
            handoff_draft=AgentHandoffDraft(
                session_id=final.session_id,
                template_id=None,
                status="draft",
                proposed_action="Automate the browser workflow.",
                action_plan=["Review inputs."],
            ),
        ),
    )

    session = repository.create_session(Session(id="session-ui", sync_enabled=False))
    recorder.state.session_id = session.id
    recorder.state.running = True
    recorder._chunker = ActivityChunker(session.id, now_provider=lambda: datetime.now(timezone.utc))

    recorder.pause()
    recorder.resume()
    recorder.request_stop()
    recorder._shutdown()

    event_types = [event["type"] for event in emitted]
    assert "session_paused" in event_types
    assert "session_resumed" in event_types
    assert "final_pseudocode_started" in event_types
    assert "final_pseudocode_created" in event_types
    assert "workflow_template_created" in event_types
    assert "agent_handoff_created" in event_types
    assert event_types[-1] == "session_complete"

    final_event = next(event for event in emitted if event["type"] == "final_pseudocode_created")
    assert final_event["automation_score"] == 84
    assert final_event["recommended_next_action"] == "Create a reusable workflow template."


def test_recorder_skips_workflow_search_index_sync_404(tmp_path) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    config = TrackerConfig(
        db_path=tmp_path / "local_tracker.db",
        screenshot_dir=tmp_path / "screenshots",
        export_dir=tmp_path / "exports",
        enable_cloud_sync=True,
        llm_provider="mock",
    )
    emitted: list[dict] = []

    class _Search404Client(_DummyClient):
        def upload_search_index_record(self, payload: dict) -> dict:
            response = requests.Response()
            response.status_code = 404
            response.url = "https://example.com/api/database/records/workflow_search_index"
            raise requests.HTTPError("404 Client Error: Not Found", response=response)

    recorder = SessionRecorder(
        config,
        repository,
        MockLLMClient(),
        _Search404Client(),
        event_sink=emitted.append,
    )

    record = repository.save_workflow_search_index(
        WorkflowSearchIndexRecord(
            session_id="session-404",
            template_id=None,
            searchable_text="browser workflow",
            tags=["browser"],
        )
    )
    recorder._upload_workflow_search_index_record(record)

    stored = repository.get_workflow_search_index_record("session-404")
    assert stored is not None and stored.synced is True
    assert [event["type"] for event in emitted] == [
        "insforge_sync_started",
        "insforge_sync_complete",
    ]


def test_recorder_skips_workflow_template_sync_404(tmp_path) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    config = TrackerConfig(
        db_path=tmp_path / "local_tracker.db",
        screenshot_dir=tmp_path / "screenshots",
        export_dir=tmp_path / "exports",
        enable_cloud_sync=True,
        llm_provider="mock",
    )
    emitted: list[dict] = []

    class _Template404Client(_DummyClient):
        def upload_workflow_template(self, payload: dict) -> dict:
            response = requests.Response()
            response.status_code = 404
            response.url = "https://example.com/api/database/records/workflow_templates"
            raise requests.HTTPError("404 Client Error: Not Found", response=response)

    recorder = SessionRecorder(
        config,
        repository,
        MockLLMClient(),
        _Template404Client(),
        event_sink=emitted.append,
    )

    template = repository.save_workflow_template(
        WorkflowTemplate(
            session_id="session-404",
            title="Open Docs",
            description="Reusable browser workflow",
            category="browser_admin_workflow",
            tags=["browser"],
            pseudocode=["Step 1. Open Docs."],
            plain_text="1. Open Docs.",
        )
    )
    recorder._upload_workflow_template(template)

    stored = repository.get_workflow_template(template.id)
    assert stored is not None and stored.synced is True
    assert [event["type"] for event in emitted] == [
        "insforge_sync_started",
        "insforge_sync_complete",
    ]


def test_recorder_skips_workflow_insight_sync_404(tmp_path) -> None:
    repository = LocalSQLiteRepository(tmp_path / "local_tracker.db")
    config = TrackerConfig(
        db_path=tmp_path / "local_tracker.db",
        screenshot_dir=tmp_path / "screenshots",
        export_dir=tmp_path / "exports",
        enable_cloud_sync=True,
        llm_provider="mock",
    )
    emitted: list[dict] = []

    class _Insight404Client(_DummyClient):
        def upload_workflow_insight(self, payload: dict) -> dict:
            response = requests.Response()
            response.status_code = 404
            response.url = "https://example.com/api/database/records/workflow_insights"
            raise requests.HTTPError("404 Client Error: Not Found", response=response)

    recorder = SessionRecorder(
        config,
        repository,
        MockLLMClient(),
        _Insight404Client(),
        event_sink=emitted.append,
    )

    insight = repository.save_workflow_insight(
        WorkflowInsight(
            session_id="session-404",
            summary="A browser workflow.",
            main_apps=["Chrome"],
            detected_task_type="browser_admin_workflow",
            tags=["browser"],
            automation_score=82,
            automation_reason="Highly repeatable.",
            recommended_next_action="Create a reusable workflow template.",
        )
    )
    recorder._upload_workflow_insight(insight)

    stored = repository.get_workflow_insight(insight.session_id)
    assert stored is not None and stored.synced is True
    assert [event["type"] for event in emitted] == [
        "insforge_sync_started",
        "insforge_sync_complete",
    ]
