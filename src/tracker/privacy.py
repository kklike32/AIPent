from __future__ import annotations

SENSITIVE_KEYWORDS = (
    "password",
    "passcode",
    "1password",
    "keychain",
    "auth",
    "login",
    "secret",
)


def is_sensitive_window_title(window_title: str | None) -> bool:
    if not window_title:
        return False
    lower = window_title.lower()
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


def is_sensitive_ocr_text(text: str | None) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(keyword in lower for keyword in SENSITIVE_KEYWORDS)
