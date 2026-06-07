from __future__ import annotations

from collections.abc import Mapping

SENSITIVE_KEYWORDS = (
    "password",
    "passcode",
    "1password",
    "keychain",
    "auth",
    "login",
    "secret",
)


def is_sensitive_window_title(window_title: object | None) -> bool:
    if not window_title:
        return False
    lower = str(window_title).lower()
    return any(keyword in lower for keyword in SENSITIVE_KEYWORDS)


def redact_text(text: str, max_len: int = 200) -> str:
    sanitized = " ".join(text.split())
    if len(sanitized) <= max_len:
        return sanitized
    return sanitized[: max_len - 3] + "..."


def should_capture_shortcut(modifiers: set[str], key_name: str | None) -> bool:
    if not key_name:
        return False
    if key_name in {"shift", "ctrl", "alt", "cmd"}:
        return False
    return bool(modifiers)


def is_sensitive_ocr_text(text: object | None) -> bool:
    if not text:
        return False
    lower = str(text).lower()
    return any(keyword in lower for keyword in SENSITIVE_KEYWORDS)


ALLOWED_REMOTE_FIELDS = {
    "sessions": {
        "id",
        "user_id",
        "started_at",
        "ended_at",
        "session_name",
        "device_name",
        "os_name",
        "visibility",
    },
    "chunk_summaries": {
        "id",
        "session_id",
        "chunk_index",
        "started_at",
        "ended_at",
        "summary",
        "observed_apps",
        "confidence",
        "user_id",
    },
    "final_pseudocode": {
        "id",
        "session_id",
        "pseudocode",
        "plain_text",
        "suggestions",
        "user_id",
    },
    "workflow_insights": {
        "id",
        "session_id",
        "summary",
        "main_apps",
        "detected_task_type",
        "tags",
        "automation_score",
        "automation_reason",
        "recommended_next_action",
        "user_id",
    },
    "workflow_templates": {
        "id",
        "session_id",
        "title",
        "description",
        "category",
        "tags",
        "pseudocode",
        "plain_text",
        "user_id",
        "visibility",
        "shared_with_team",
        "created_from",
    },
    "agent_handoff_queue": {
        "id",
        "session_id",
        "template_id",
        "status",
        "proposed_action",
        "action_plan",
        "requires_user_approval",
        "approved_at",
        "executed_at",
        "user_id",
    },
    "workflow_search_index": {
        "id",
        "session_id",
        "template_id",
        "searchable_text",
        "tags",
        "user_id",
        "visibility",
    },
    "automation_profiles": {
        "id",
        "user_id",
        "org_id",
        "template_id",
        "name",
        "description",
        "status",
    },
    "profile_steps": {
        "id",
        "profile_id",
        "position",
        "title",
        "instruction",
        "expected_result",
    },
    "skills": {
        "id",
        "org_id",
        "name",
        "description",
        "status",
        "category",
        "current_version",
        "created_by",
    },
    "skill_versions": {
        "id",
        "skill_id",
        "version",
        "definition",
        "is_current",
        "created_by",
    },
}


FORBIDDEN_REMOTE_KEYS = {
    "ocr_text",
    "screenshots",
    "screenshot",
    "audio",
    "audio_path",
    "audio_recording",
    "mouse_events",
    "keyboard_events",
    "keyboard_shortcuts",
    "metadata",
    "storage_path",
    "local_path",
    "window_title",
    "app_name",
    "event_type",
    "timestamp",
    "text",
    "x",
    "y",
    "button",
    "key",
    "modifiers",
    "raw_events",
    "events",
}


def assert_remote_payload_allowed(table: str, payload: Mapping[str, object]) -> None:
    allowed_keys = ALLOWED_REMOTE_FIELDS.get(table)
    if allowed_keys is None:
        raise ValueError(f"Unknown remote table: {table}")

    payload_keys = set(payload.keys())
    if not payload_keys.issubset(allowed_keys):
        disallowed = sorted(payload_keys - allowed_keys)
        raise ValueError(f"Payload for {table} contains disallowed keys: {disallowed}")

    forbidden = sorted(key for key in payload_keys if key in FORBIDDEN_REMOTE_KEYS)
    if forbidden:
        raise ValueError(f"Payload for {table} contains forbidden privacy keys: {forbidden}")
