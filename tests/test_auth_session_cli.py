from pathlib import Path

from typer.testing import CliRunner

from tracker.auth_session import AuthSession, mask_token, save_auth_session
from tracker.cli import app


def test_mask_token_hides_most_characters() -> None:
    masked = mask_token("abcdefghijklmnopqrstuvwxyz")
    assert masked.startswith("********")
    assert masked.endswith("wxyz")


def test_tracker_auth_logout_clears_stored_token(tmp_path, monkeypatch) -> None:
    auth_dir = tmp_path / ".computer-usage-tracker"
    auth_file = auth_dir / "auth.json"

    monkeypatch.setattr("tracker.auth_session.AUTH_DIR", auth_dir)
    monkeypatch.setattr("tracker.auth_session.AUTH_FILE", auth_file)

    save_auth_session(AuthSession(token="test-token", user_id="user-1", email="a@example.com"))
    assert auth_file.exists()

    result = CliRunner().invoke(app, ["auth", "logout"])

    assert result.exit_code == 0
    assert auth_file.exists() is False
