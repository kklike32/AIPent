from pathlib import Path

from tracker.config import TrackerConfig
from tracker.events import ActivityChunk
from tracker.llm.gemini_vertex import CHUNK_SUMMARY_PROMPT, VertexGeminiClient


def test_chunk_summary_prompt_requests_action_level_detail() -> None:
    assert "Describe the visible workflow in chronological order." in CHUNK_SUMMARY_PROMPT
    assert "button, menu, field, link, or item" in CHUNK_SUMMARY_PROMPT
    assert "Mention what likely changed on screen after the action" in CHUNK_SUMMARY_PROMPT
    assert 'Do not mention screenshots, OCR, or "the image shows".' in CHUNK_SUMMARY_PROMPT


def test_summarize_chunk_sends_interaction_hints(monkeypatch) -> None:
    client = VertexGeminiClient(TrackerConfig(gemini_api_key="test-key"))
    captured: dict[str, object] = {}

    def fake_generate_content_api_key(prompt: str, payload: object, screenshots: list[Path]) -> dict:
        captured["prompt"] = prompt
        captured["payload"] = payload
        captured["screenshots"] = screenshots
        return {
            "summary": (
                "The user switched to the Docs draft, clicked into a paragraph, "
                "and likely used paste to insert copied text before continuing to edit."
            ),
            "observed_apps": ["Chrome"],
            "confidence": "high",
        }

    monkeypatch.setattr(client, "_generate_content_api_key", fake_generate_content_api_key)

    chunk = ActivityChunk(
        session_id="session-1",
        chunk_index=3,
        started_at="2026-01-01T00:00:18+00:00",
        ended_at="2026-01-01T00:00:24+00:00",
        screenshots=[Path("/tmp/one.png"), Path("/tmp/two.png")],
        mouse_events=[
            {"timestamp": "2026-01-01T00:00:19+00:00", "button": "left"},
            {"timestamp": "2026-01-01T00:00:21+00:00", "button": "left"},
        ],
        keyboard_shortcuts=[{"timestamp": "2026-01-01T00:00:20+00:00", "shortcut": "cmd+v"}],
        active_windows=[
            {
                "timestamp": "2026-01-01T00:00:18+00:00",
                "app_name": "Chrome",
                "window_title": "Quarterly plan - Google Docs",
            },
            {
                "timestamp": "2026-01-01T00:00:22+00:00",
                "app_name": "Chrome",
                "window_title": "Quarterly plan - Google Docs",
            },
        ],
        ocr_text=["Quarterly goals", "Launch timeline"],
    )

    summary = client.summarize_chunk(chunk)

    assert summary.summary.startswith("The user switched to the Docs draft")
    assert summary.observed_apps == ["Chrome"]
    assert captured["prompt"] == CHUNK_SUMMARY_PROMPT
    assert captured["screenshots"] == chunk.screenshots

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["chunk_index"] == 3
    assert payload["interaction_hints"] == {
        "screenshot_count": 2,
        "mouse_click_count": 2,
        "mouse_buttons": ["left", "left"],
        "keyboard_shortcut_count": 1,
        "keyboard_shortcuts": ["cmd+v"],
        "window_sequence": [
            {
                "app_name": "Chrome",
                "window_title": "Quarterly plan - Google Docs",
            }
        ],
        "ocr_snippets": ["Quarterly goals", "Launch timeline"],
    }
