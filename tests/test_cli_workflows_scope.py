from typer.testing import CliRunner

from tracker.cli import app
from tracker.config import TrackerConfig


class _FakeClient:
    def __init__(self) -> None:
        self.list_scope = None
        self.search_scope = None

    def list_workflow_templates(self, limit: int = 10, scope: str = "mine"):
        self.list_scope = scope
        return []

    def list_workflow_insights(self, session_id=None, limit: int = 10):
        return []

    def search_workflows(self, query: str, limit: int = 10, scope: str = "mine"):
        self.search_scope = scope
        return []


def _config() -> TrackerConfig:
    return TrackerConfig(
        enable_cloud_sync=True,
        insforge_base_url="https://api.example.com",
        insforge_project_id="proj",
        insforge_api_key="key",
        insforge_auth_token="token",
        insforge_current_user_id="user-1",
    )


def test_workflows_list_mine_uses_mine_scope(monkeypatch) -> None:
    fake = _FakeClient()
    monkeypatch.setattr("tracker.cli._build_config", lambda *args, **kwargs: _config())
    monkeypatch.setattr("tracker.cli._maybe_client", lambda _config: fake)

    result = CliRunner().invoke(app, ["workflows", "list", "--mine"])

    assert result.exit_code == 0
    assert fake.list_scope == "mine"


def test_workflows_list_team_uses_team_scope(monkeypatch) -> None:
    fake = _FakeClient()
    monkeypatch.setattr("tracker.cli._build_config", lambda *args, **kwargs: _config())
    monkeypatch.setattr("tracker.cli._maybe_client", lambda _config: fake)

    result = CliRunner().invoke(app, ["workflows", "list", "--team"])

    assert result.exit_code == 0
    assert fake.list_scope == "team"


def test_workflows_search_team_uses_team_scope(monkeypatch) -> None:
    fake = _FakeClient()
    monkeypatch.setattr("tracker.cli._build_config", lambda *args, **kwargs: _config())
    monkeypatch.setattr("tracker.cli._maybe_client", lambda _config: fake)

    result = CliRunner().invoke(app, ["workflows", "search", "spreadsheet report", "--scope", "team"])

    assert result.exit_code == 0
    assert fake.search_scope == "team"
