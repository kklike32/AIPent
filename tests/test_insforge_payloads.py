import pytest

from tracker.storage.insforge_client import InsForgeClient


class _DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload
        self.content = b"{}"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_insforge_client_summary_only_payloads(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(("POST", url, json, headers, timeout))
        return _DummyResponse({"id": "server-id"})

    client = InsForgeClient(
        "https://api.example.com",
        "test-key",
        "token",
        current_user_id="user-1",
        auth_enabled=True,
    )
    monkeypatch.setattr("tracker.storage.insforge_client.requests.post", fake_post)

    session_payload = {
        "id": "session-1",
        "user_id": "user-1",
        "started_at": "2026-01-01T00:00:00+00:00",
        "ended_at": None,
        "session_name": None,
        "device_name": "machine",
        "os_name": "Darwin",
        "visibility": "private",
    }
    summary_payload = {
        "id": "summary-1",
        "session_id": "session-1",
        "chunk_index": 0,
        "started_at": "2026-01-01T00:00:00+00:00",
        "ended_at": "2026-01-01T00:00:06+00:00",
        "summary": "Reviewed a browser page.",
        "observed_apps": ["Chrome"],
        "confidence": "high",
        "user_id": "user-1",
    }
    final_payload = {
        "id": "final-1",
        "session_id": "session-1",
        "pseudocode": ["Step 1. Review the page."],
        "plain_text": "1. Review the page.",
        "suggestions": ["Pin the document."],
        "user_id": "user-1",
    }
    insight_payload = {
        "id": "insight-1",
        "session_id": "session-1",
        "summary": "The user reviewed a browser page and documented the steps.",
        "main_apps": ["Chrome"],
        "detected_task_type": "browser_admin_workflow",
        "tags": ["browser", "automation_candidate"],
        "automation_score": 78,
        "automation_reason": "The workflow is repetitive and structured.",
        "recommended_next_action": "Create a reusable workflow template and draft a Python automation plan.",
        "user_id": "user-1",
    }
    template_payload = {
        "id": "template-1",
        "session_id": "session-1",
        "title": "Review the page",
        "description": "A reusable workflow for reviewing a page.",
        "category": "browser_admin_workflow",
        "tags": ["browser", "automation_candidate"],
        "pseudocode": ["Step 1. Review the page."],
        "plain_text": "1. Review the page.",
        "user_id": "user-1",
        "visibility": "private",
        "shared_with_team": False,
        "created_from": "session_summary",
    }
    handoff_payload = {
        "id": "handoff-1",
        "session_id": "session-1",
        "template_id": "template-1",
        "status": "draft",
        "proposed_action": "Turn the workflow into a reusable automation.",
        "action_plan": ["Review inputs", "Create a dry-run automation plan"],
        "requires_user_approval": True,
        "approved_at": None,
        "executed_at": None,
        "user_id": "user-1",
    }
    search_payload = {
        "id": "search-1",
        "session_id": "session-1",
        "template_id": "template-1",
        "searchable_text": "review page browser automation",
        "tags": ["browser", "automation_candidate"],
        "user_id": "user-1",
        "visibility": "private",
    }

    client.create_session(session_payload)
    client.upload_chunk_summary(summary_payload)
    client.upload_final_pseudocode(final_payload)
    client.upload_workflow_insight(insight_payload)
    client.upload_workflow_template(template_payload)
    client.upload_agent_handoff_draft(handoff_payload)
    client.upload_search_index_record(search_payload)

    assert calls[0][1].endswith("/api/database/records/sessions")
    assert calls[1][1].endswith("/api/database/records/chunk_summaries")
    assert calls[2][1].endswith("/api/database/records/final_pseudocode")
    assert calls[3][1].endswith("/api/database/records/workflow_insights")
    assert calls[4][1].endswith("/api/database/records/workflow_templates")
    assert calls[5][1].endswith("/api/database/records/agent_handoff_queue")
    assert calls[6][1].endswith("/api/database/records/workflow_search_index")
    assert calls[1][2] == summary_payload
    assert calls[2][2] == final_payload
    assert calls[3][2] == insight_payload
    assert calls[4][2] == template_payload
    assert calls[5][2] == handoff_payload
    assert calls[6][2] == search_payload
    assert calls[0][3]["Authorization"] == "Bearer token"


def test_insforge_client_rejects_raw_activity_payloads():
    client = InsForgeClient(
        "https://api.example.com",
        "test-key",
        "token",
        current_user_id="user-1",
        auth_enabled=True,
    )

    with pytest.raises(ValueError):
        client.upload_chunk_summary(
            {
                "id": "summary-1",
                "session_id": "session-1",
                "chunk_index": 0,
                "started_at": "2026-01-01T00:00:00+00:00",
                "ended_at": "2026-01-01T00:00:06+00:00",
                "summary": "Reviewed a browser page.",
                "observed_apps": ["Chrome"],
                "confidence": "high",
                "user_id": "user-1",
                "ocr_text": ["secret"],
            }
        )

    with pytest.raises(ValueError):
        client.upload_search_index_record(
            {
                "id": "search-1",
                "session_id": "session-1",
                "template_id": "template-1",
                "searchable_text": "safe summary",
                "tags": ["browser"],
                "user_id": "user-1",
                "visibility": "private",
                "raw_events": [{"event_type": "mouse_click"}],
            }
        )


def test_insforge_client_requires_auth_token_when_enabled():
    client = InsForgeClient(
        "https://api.example.com",
        "test-key",
        auth_token=None,
        current_user_id="user-1",
        auth_enabled=True,
    )

    with pytest.raises(ValueError):
        client.create_session(
            {
                "id": "session-1",
                "user_id": "user-1",
                "started_at": "2026-01-01T00:00:00+00:00",
                "ended_at": None,
                "session_name": None,
                "device_name": "machine",
                "os_name": "Darwin",
                "visibility": "private",
            }
        )


def test_insforge_client_marks_team_template_shared(monkeypatch):
    payloads = []

    def fake_post(url, json, headers, timeout):
        payloads.append(json)
        return _DummyResponse({"id": "template-1"})

    monkeypatch.setattr("tracker.storage.insforge_client.requests.post", fake_post)
    client = InsForgeClient(
        "https://api.example.com",
        "test-key",
        "token",
        current_user_id="user-1",
        auth_enabled=True,
    )
    client.upload_workflow_template(
        {
            "id": "template-1",
            "session_id": "session-1",
            "user_id": "other-user",
            "title": "Review the page",
            "description": "A reusable workflow for reviewing a page.",
            "category": "browser_admin_workflow",
            "tags": ["browser", "automation_candidate"],
            "pseudocode": ["Step 1. Review the page."],
            "plain_text": "1. Review the page.",
            "visibility": "team",
            "created_from": "session_summary",
        }
    )

    assert payloads[0]["user_id"] == "user-1"
    assert payloads[0]["shared_with_team"] is True


def test_insforge_client_filters_team_and_mine_scopes(monkeypatch):
    client = InsForgeClient(
        "https://api.example.com",
        "test-key",
        "token",
        current_user_id="user-1",
        auth_enabled=True,
    )

    monkeypatch.setattr(
        client,
        "_list_records",
        lambda _table, _params=None: [
            {"id": "a", "user_id": "user-1", "visibility": "private", "searchable_text": "report"},
            {"id": "b", "user_id": "user-2", "visibility": "team", "searchable_text": "report"},
            {"id": "c", "user_id": "user-2", "visibility": "private", "searchable_text": "report"},
        ],
    )

    mine = client.search_workflows("report", scope="mine")
    team = client.search_workflows("report", scope="team")

    assert [record["id"] for record in mine] == ["a"]
    assert [record["id"] for record in team] == ["a", "b"]
