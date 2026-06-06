from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


AUTH_DIR = Path.home() / ".computer-usage-tracker"
AUTH_FILE = AUTH_DIR / "auth.json"


@dataclass(slots=True)
class AuthSession:
    token: str
    user_id: str | None = None
    email: str | None = None


def _auth_file(path: Path | None = None) -> Path:
    return path or AUTH_FILE


def mask_token(token: str | None) -> str:
    if not token:
        return ""
    suffix = token[-4:] if len(token) >= 4 else token
    return f"{'*' * 8}{suffix}"


def load_auth_session(path: Path | None = None) -> AuthSession | None:
    auth_path = _auth_file(path)
    if not auth_path.exists():
        return None
    try:
        payload = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    token = str(payload.get("token", "")).strip()
    if not token:
        return None
    user_id = payload.get("user_id")
    email = payload.get("email")
    return AuthSession(
        token=token,
        user_id=str(user_id) if user_id else None,
        email=str(email) if email else None,
    )


def save_auth_session(session: AuthSession, path: Path | None = None) -> None:
    auth_path = _auth_file(path)
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "token": session.token,
        "user_id": session.user_id,
        "email": session.email,
    }
    auth_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    auth_path.chmod(0o600)


def clear_auth_session(path: Path | None = None) -> None:
    auth_path = _auth_file(path)
    if auth_path.exists():
        auth_path.unlink()
