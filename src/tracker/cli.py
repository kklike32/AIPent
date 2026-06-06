from __future__ import annotations

import signal
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .auth_session import AuthSession, clear_auth_session, load_auth_session, save_auth_session
from .config import TrackerConfig
from .jsonl import build_jsonl_sink
from .llm import build_llm_client
from .recorder import SessionRecorder
from .storage.insforge_client import InsForgeClient
from .storage.local_sqlite import LocalSQLiteRepository
from .summarization import generate_final_pseudocode
from .sync import SyncService
from .workflows import build_workflow_artifacts

app = typer.Typer(help="Track desktop usage sessions and summarize workflows.")
auth_app = typer.Typer(help="Manage InsForge auth token reuse for desktop sync.")
workflows_app = typer.Typer(help="Inspect privacy-safe workflow intelligence records.")
app.add_typer(auth_app, name="auth")
app.add_typer(workflows_app, name="workflows")
console = Console()

ALLOWED_VISIBILITY = {"private", "team"}
ALLOWED_WORKFLOW_SCOPE = {"mine", "team"}


def _build_config(
    db_path: Optional[str],
    cloud_sync: Optional[bool] = None,
    llm_provider: Optional[str] = None,
    screenshot_interval: Optional[int] = None,
    chunk_interval: Optional[int] = None,
    workflow_visibility: Optional[str] = None,
) -> TrackerConfig:
    config = TrackerConfig.from_env()
    auth_session = load_auth_session()
    if auth_session and not config.insforge_auth_token:
        config.insforge_auth_token = auth_session.token
    if auth_session and not config.insforge_current_user_id:
        config.insforge_current_user_id = auth_session.user_id
    if db_path:
        config.db_path = Path(db_path)
    if cloud_sync is not None:
        config.enable_cloud_sync = cloud_sync
    if llm_provider:
        config.llm_provider = llm_provider
    if screenshot_interval is not None:
        config.screenshot_interval_seconds = screenshot_interval
    if chunk_interval is not None:
        config.chunk_interval_seconds = chunk_interval
    if workflow_visibility:
        config.workflow_visibility = workflow_visibility
    else:
        config.workflow_visibility = config.default_workflow_visibility
    config.ensure_directories()
    return config


def _get_session_id(repository: LocalSQLiteRepository, session_id: Optional[str]) -> str:
    if session_id:
        return session_id
    latest = repository.get_latest_session()
    chosen = latest.id if latest else None
    if chosen is None:
        raise typer.BadParameter("No sessions found.")
    return chosen


def _maybe_client(config: TrackerConfig) -> InsForgeClient | None:
    if not (config.enable_cloud_sync and config.has_insforge_credentials()):
        return None
    return InsForgeClient.from_config(config)


def _validate_visibility(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_VISIBILITY:
        raise typer.BadParameter("Visibility must be one of: private, team.")
    return normalized


def _validate_scope(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_WORKFLOW_SCOPE:
        raise typer.BadParameter("Scope must be one of: mine, team.")
    return normalized


def _schema_sql() -> str:
    return """create table if not exists sessions (
  id uuid primary key,
    user_id uuid references auth.users(id),
    visibility text not null default 'private',
  started_at timestamptz not null,
  ended_at timestamptz nullable,
  session_name text nullable,
  device_name text nullable,
  os_name text nullable,
  created_at timestamptz default now()
);

create table if not exists chunk_summaries (
  id uuid primary key,
  session_id uuid references sessions(id),
    user_id uuid references auth.users(id),
  chunk_index integer not null,
  started_at timestamptz not null,
  ended_at timestamptz not null,
  summary text not null,
  observed_apps jsonb nullable,
  confidence text nullable,
  created_at timestamptz default now()
);

create table if not exists final_pseudocode (
  id uuid primary key,
  session_id uuid references sessions(id),
    user_id uuid references auth.users(id),
  pseudocode jsonb not null,
  plain_text text not null,
  suggestions jsonb nullable,
  created_at timestamptz default now()
);

create table if not exists workflow_templates (
  id uuid primary key,
  session_id uuid references sessions(id),
    user_id uuid references auth.users(id),
  title text not null,
  description text nullable,
  category text nullable,
  tags jsonb default '[]'::jsonb,
  pseudocode jsonb not null,
  plain_text text not null,
    visibility text not null default 'private',
    shared_with_team boolean not null default false,
  created_from text default 'session_summary',
  created_at timestamptz default now()
);

create table if not exists workflow_insights (
  id uuid primary key,
  session_id uuid references sessions(id),
    user_id uuid references auth.users(id),
  summary text not null,
  main_apps jsonb default '[]'::jsonb,
  detected_task_type text nullable,
  tags jsonb default '[]'::jsonb,
  automation_score integer not null,
  automation_reason text nullable,
  recommended_next_action text nullable,
  created_at timestamptz default now()
);

create table if not exists agent_handoff_queue (
  id uuid primary key,
  session_id uuid references sessions(id),
    user_id uuid references auth.users(id),
  template_id uuid nullable references workflow_templates(id),
  status text default 'draft',
  proposed_action text not null,
  action_plan jsonb not null,
  requires_user_approval boolean default true,
  approved_at timestamptz nullable,
  executed_at timestamptz nullable,
  created_at timestamptz default now()
);

create table if not exists workflow_search_index (
  id uuid primary key,
  session_id uuid references sessions(id),
    user_id uuid references auth.users(id),
  template_id uuid nullable references workflow_templates(id),
  searchable_text text not null,
  tags jsonb default '[]'::jsonb,
    visibility text not null default 'private',
  created_at timestamptz default now()
);
"""


def _setup_markdown() -> str:
    return """# Privacy-Safe Workflow Intelligence Backend

## Remote data model

InsForge stores only:

- session metadata
- 6-second chunk summaries
- final pseudocode
- workflow insights
- workflow templates
- workflow search records
- automation scores
- suggested next actions
- draft agent handoff plans

InsForge does not store screenshots, OCR text, mouse events, keyboard events, or local event logs.

## Environment

Copy `.env.example` to `.env` and set the InsForge and Vertex values you need.

## Schema

Run SQL from `insforge_schema.sql` in your InsForge project.

## Usage

Start local capture:

```bash
tracker start --llm-provider mock
```

Enable the privacy-safe workflow intelligence backend:

```bash
tracker start --cloud-sync --llm-provider vertex_gemini
```
"""


def _render_template_table(records: list[object]) -> None:
    table = Table(title="Workflow Templates")
    table.add_column("Title")
    table.add_column("Created By")
    table.add_column("Visibility")
    table.add_column("Category")
    table.add_column("Automation Score")
    table.add_column("Created At")
    for record in records:
        created_at = getattr(record, "created_at", "") or ""
        automation_score = getattr(record, "automation_score", "")
        created_by = getattr(record, "owner_email", None) or getattr(record, "user_id", "")
        visibility = getattr(record, "visibility", "private")
        table.add_row(
            str(getattr(record, "title", "")),
            str(created_by or ""),
            str(visibility),
            str(getattr(record, "category", "")),
            str(automation_score),
            str(created_at),
        )
    console.print(table)


def _generate_workflow_outputs(
    config: TrackerConfig,
    repository: LocalSQLiteRepository,
    session_id: str,
) -> tuple[object, object | None, object, object | None]:
    summaries = repository.get_chunk_summaries(session_id)
    if not summaries:
        raise typer.BadParameter(f"No chunk summaries found for session {session_id}.")
    final = repository.get_final_pseudocode(session_id)
    if final is None:
        raise typer.BadParameter(f"No final pseudocode found for session {session_id}.")

    artifacts = build_workflow_artifacts(
        final,
        summaries,
        enable_template_creation=config.enable_workflow_template_creation,
        enable_agent_handoff_drafts=config.enable_agent_handoff_drafts,
        handoff_threshold=config.agent_handoff_automation_score_threshold,
    )
    visibility = "team" if config.workflow_visibility == "team" and config.enable_team_sharing else "private"
    user_id = config.insforge_current_user_id
    artifacts.insight.user_id = user_id
    artifacts.search_index.user_id = user_id
    artifacts.search_index.visibility = visibility
    if artifacts.template is not None:
        artifacts.template.user_id = user_id
        artifacts.template.visibility = visibility
        artifacts.template.shared_with_team = visibility == "team"
    if artifacts.handoff_draft is not None:
        artifacts.handoff_draft.user_id = user_id
    insight = repository.save_workflow_insight(artifacts.insight)
    template = None
    if artifacts.template is not None:
        template = repository.save_workflow_template(artifacts.template)
        artifacts.search_index.template_id = template.id
    search_record = repository.save_workflow_search_index(artifacts.search_index)
    handoff = None
    if artifacts.handoff_draft is not None:
        handoff = repository.save_agent_handoff_draft(artifacts.handoff_draft)

    client = _maybe_client(config)
    if client:
        SyncService(repository, client, config).sync_session(session_id)
    return insight, template, search_record, handoff


@app.command("init-backend")
def init_backend(
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
) -> None:
    """Generate InsForge backend setup artifacts and print expected schema."""
    config = _build_config(db_path)
    Path("insforge_schema.sql").write_text(_schema_sql(), encoding="utf-8")
    Path("INSFORGE_SETUP.md").write_text(_setup_markdown(), encoding="utf-8")

    console.print(Panel.fit(_schema_sql(), title="Expected InsForge Schema"))
    if config.has_insforge_credentials():
        console.print("[green]InsForge env vars found.[/green] Setup artifacts regenerated.")
    else:
        console.print("[yellow]Missing InsForge env vars.[/yellow] Setup artifacts regenerated.")


@auth_app.command("login")
def auth_login(
    token: Optional[str] = typer.Option(
        None,
        "--token",
        help="InsForge auth token copied from an existing authenticated frontend session.",
    ),
) -> None:
    """Store an InsForge auth token for this desktop tracker session."""
    auth_token = (token or "").strip()
    if not auth_token:
        auth_token = typer.prompt("Paste InsForge auth token", hide_input=True).strip()
    if not auth_token:
        raise typer.BadParameter("Auth token is required.")

    config = _build_config(None)
    user_id: str | None = None
    email: str | None = None

    if config.has_insforge_credentials():
        client = InsForgeClient(
            base_url=str(config.insforge_base_url),
            api_key=str(config.insforge_api_key),
            auth_token=auth_token,
            current_user_id=config.insforge_current_user_id,
            auth_enabled=True,
            summaries_table=config.insforge_summaries_table,
            final_table=config.insforge_final_table,
            workflow_insights_table=config.insforge_workflow_insights_table,
            workflow_templates_table=config.insforge_workflow_templates_table,
            agent_handoff_table=config.insforge_agent_handoff_table,
            workflow_search_table=config.insforge_workflow_search_table,
        )
        try:
            user = client.get_current_user()
            user_id = user.get("id") if isinstance(user.get("id"), str) else None
            email = user.get("email") if isinstance(user.get("email"), str) else None
        except Exception as exc:
            raise typer.BadParameter(f"Failed to validate InsForge auth token: {exc}") from exc

    save_auth_session(AuthSession(token=auth_token, user_id=user_id, email=email))
    console.print("[bold green]InsForge auth token saved.[/bold green]")
    if user_id or email:
        console.print(f"User: {email or '(email unavailable)'}")
        console.print(f"User ID: {user_id or '(id unavailable)'}")


@auth_app.command("status")
def auth_status() -> None:
    """Show InsForge auth status for the desktop tracker."""
    config = _build_config(None)
    session = load_auth_session()
    if session is None:
        console.print("[yellow]Not connected.[/yellow] No local InsForge auth token is stored.")
        if config.insforge_project_id:
            console.print(f"Project: {config.insforge_project_id}")
        return

    user_id = session.user_id
    email = session.email
    token_validated = False
    token_expired = False

    if config.has_insforge_credentials():
        client = InsForgeClient(
            base_url=str(config.insforge_base_url),
            api_key=str(config.insforge_api_key),
            auth_token=session.token,
            current_user_id=session.user_id,
            auth_enabled=True,
            summaries_table=config.insforge_summaries_table,
            final_table=config.insforge_final_table,
            workflow_insights_table=config.insforge_workflow_insights_table,
            workflow_templates_table=config.insforge_workflow_templates_table,
            agent_handoff_table=config.insforge_agent_handoff_table,
            workflow_search_table=config.insforge_workflow_search_table,
        )
        try:
            user = client.get_current_user()
            token_validated = True
            user_id = user.get("id") if isinstance(user.get("id"), str) else user_id
            email = user.get("email") if isinstance(user.get("email"), str) else email
        except Exception:
            token_expired = True

    if token_expired:
        console.print("[red]Token expired or invalid.[/red]")
    elif token_validated:
        console.print("[bold green]Connected.[/bold green]")
    else:
        console.print("[bold green]Connected (unverified).[/bold green]")

    console.print(f"Project: {config.insforge_project_id or '(not configured)'}")
    console.print(f"User: {email or '(email unavailable)'}")
    console.print(f"User ID: {user_id or '(id unavailable)'}")


@auth_app.command("logout")
def auth_logout() -> None:
    """Clear local InsForge auth token storage."""
    clear_auth_session()
    console.print("[bold green]InsForge auth token cleared.[/bold green]")


@app.command()
def start(
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
    screenshot_interval: Optional[int] = typer.Option(
        None,
        min=1,
        help="Screenshot interval in seconds. Defaults to env.",
    ),
    chunk_interval: Optional[int] = typer.Option(
        None,
        min=1,
        help="Chunk interval in seconds. Defaults to env.",
    ),
    ocr: bool = typer.Option(True, "--ocr/--no-ocr", help="Toggle OCR."),
    cloud_sync: bool = typer.Option(False, "--cloud-sync", help="Enable cloud sync for this run."),
    no_cloud_sync: bool = typer.Option(
        False,
        "--no-cloud-sync",
        help="Disable cloud sync for this run.",
    ),
    llm_provider: Optional[str] = typer.Option(
        None,
        help="LLM provider override, for example `vertex_gemini` or `mock`.",
    ),
    visibility: str = typer.Option(
        "private",
        "--visibility",
        help="Workflow visibility for safe shared records: private or team.",
    ),
    jsonl: bool = typer.Option(
        False,
        "--jsonl",
        help="Emit machine-readable JSONL progress events to stdout.",
    ),
) -> None:
    """Start a new tracking session and record until Ctrl+C."""
    cloud_sync_override: Optional[bool] = None
    if cloud_sync and no_cloud_sync:
        raise typer.BadParameter("Choose either --cloud-sync or --no-cloud-sync.")
    if cloud_sync:
        cloud_sync_override = True
    if no_cloud_sync:
        cloud_sync_override = False
    normalized_visibility = _validate_visibility(visibility)
    config = _build_config(
        db_path,
        cloud_sync=cloud_sync_override,
        llm_provider=llm_provider,
        screenshot_interval=screenshot_interval,
        chunk_interval=chunk_interval,
        workflow_visibility=normalized_visibility,
    )
    if normalized_visibility == "team" and not config.enable_team_sharing:
        raise typer.BadParameter("Team sharing is disabled. Set ENABLE_TEAM_SHARING=true to use --visibility team.")
    config.ocr_enabled = ocr
    repository = LocalSQLiteRepository(config.db_path)
    client = _maybe_client(config)
    llm_client = build_llm_client(config, config.llm_provider)
    recorder = SessionRecorder(
        config,
        repository,
        llm_client=llm_client,
        insforge_client=client,
        event_sink=build_jsonl_sink() if jsonl else None,
    )

    previous_sigint = signal.getsignal(signal.SIGINT)
    previous_sigusr1 = signal.getsignal(signal.SIGUSR1) if hasattr(signal, "SIGUSR1") else None
    previous_sigusr2 = signal.getsignal(signal.SIGUSR2) if hasattr(signal, "SIGUSR2") else None

    def handle_stop(_signum: int, _frame: object) -> None:
        recorder.request_stop()

    def handle_pause(_signum: int, _frame: object) -> None:
        recorder.pause()

    def handle_resume(_signum: int, _frame: object) -> None:
        recorder.resume()

    signal.signal(signal.SIGINT, handle_stop)
    if hasattr(signal, "SIGUSR1"):
        signal.signal(signal.SIGUSR1, handle_pause)
    if hasattr(signal, "SIGUSR2"):
        signal.signal(signal.SIGUSR2, handle_resume)

    if not jsonl:
        console.print("[bold green]Tracking started.[/bold green] Press Ctrl+C to stop.")
    try:
        session_id = recorder.run()
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
        if previous_sigusr1 is not None and hasattr(signal, "SIGUSR1"):
            signal.signal(signal.SIGUSR1, previous_sigusr1)
        if previous_sigusr2 is not None and hasattr(signal, "SIGUSR2"):
            signal.signal(signal.SIGUSR2, previous_sigusr2)

    if not jsonl:
        console.print(f"[bold]Session stopped:[/bold] {session_id}")

    final = repository.get_final_pseudocode(session_id)
    if final and not jsonl:
        console.print(Panel.fit(final.plain_text, title=f"Session {session_id} Final Pseudocode"))


@app.command("summarize-final")
def summarize_final(
    session_id: Optional[str] = typer.Option(None, help="Session ID to summarize."),
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
    llm_provider: Optional[str] = typer.Option(None, help="LLM provider override."),
) -> None:
    """Generate final pseudocode from stored chunk summaries."""
    config = _build_config(db_path, llm_provider=llm_provider)
    repository = LocalSQLiteRepository(config.db_path)
    chosen_session_id = _get_session_id(repository, session_id)
    summaries = repository.get_chunk_summaries(chosen_session_id)
    if not summaries:
        raise typer.BadParameter(f"No chunk summaries found for session {chosen_session_id}.")

    final = generate_final_pseudocode(build_llm_client(config, config.llm_provider), summaries)
    repository.save_final_pseudocode(final)
    _generate_workflow_outputs(config, repository, chosen_session_id)
    console.print(Panel.fit(final.plain_text, title=f"Session {chosen_session_id} Final Pseudocode"))


@app.command()
def summarize(
    session_id: Optional[str] = typer.Option(None, help="Session ID to summarize."),
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
    llm_provider: Optional[str] = typer.Option(None, help="LLM provider override."),
) -> None:
    """Backward-compatible alias for summarize-final."""
    summarize_final(session_id=session_id, db_path=db_path, llm_provider=llm_provider)


@app.command("sync-summaries")
def sync_summaries(
    session_id: str = typer.Option(..., help="Session ID to sync."),
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
) -> None:
    """Upload privacy-safe workflow records for one session."""
    config = _build_config(db_path, cloud_sync=True)
    client = _maybe_client(config)
    if client is None:
        raise typer.BadParameter("Missing InsForge credentials in environment.")
    repository = LocalSQLiteRepository(config.db_path)
    result = SyncService(repository, client, config).sync_session(session_id)
    console.print(f"[bold green]Workflow sync complete:[/bold green] {result}")


@app.command()
def sync(
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
) -> None:
    """Upload unsynced sessions, summaries, workflow records, and final pseudocode."""
    config = _build_config(db_path, cloud_sync=True)
    client = _maybe_client(config)
    if client is None:
        raise typer.BadParameter("Missing InsForge credentials in environment.")
    repository = LocalSQLiteRepository(config.db_path)
    result = SyncService(repository, client, config).sync_all()
    console.print(f"[bold green]Sync complete:[/bold green] {result}")


@app.command()
def export(
    session_id: str = typer.Option(..., help="Session ID to export."),
    format: str = typer.Option("markdown", help="Export format."),
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
    output: Optional[str] = typer.Option(None, help="Output path override."),
) -> None:
    """Export final pseudocode summary to markdown."""
    config = _build_config(db_path)
    repository = LocalSQLiteRepository(config.db_path)

    if format.lower() != "markdown":
        raise typer.BadParameter("Only markdown export is supported in this prototype.")

    final = repository.get_final_pseudocode(session_id)
    if final is None:
        raise typer.BadParameter(f"No final pseudocode found for session {session_id}.")

    output_path = Path(output) if output else config.export_dir / f"session_{session_id}_summary.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suggestion_lines = "\n".join(
        f"- Suggestion {idx}: {text}" for idx, text in enumerate(final.suggestions, start=1)
    )
    markdown = (
        f"# Session {session_id} Summary\n\n"
        f"## Pseudocode\n\n{final.plain_text}\n\n"
        f"## Suggestions\n\n{suggestion_lines or '- None'}\n"
    )
    output_path.write_text(markdown, encoding="utf-8")
    console.print(f"[bold green]Exported:[/bold green] {output_path}")


@workflows_app.command("list")
def workflows_list(
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
    limit: int = typer.Option(10, help="Maximum workflows to display."),
    mine: bool = typer.Option(False, "--mine", help="List only workflows created by current user."),
    team: bool = typer.Option(False, "--team", help="List team-visible workflows."),
) -> None:
    """Show recent synced workflows from InsForge, or local templates as fallback."""
    config = _build_config(db_path, cloud_sync=True)
    repository = LocalSQLiteRepository(config.db_path)
    client = _maybe_client(config)
    if mine and team:
        raise typer.BadParameter("Choose either --mine or --team.")
    scope = "team" if team else "mine"
    records: list[object] = []
    if client:
        templates = client.list_workflow_templates(limit=limit, scope=scope)
        for template in templates:
            session_id = str(template.get("session_id", ""))
            insights = client.list_workflow_insights(session_id=session_id, limit=1) if session_id else []
            template["automation_score"] = insights[0].get("automation_score", "") if insights else ""
            records.append(SimpleNamespace(**template))
    else:
        if scope == "team":
            templates = repository.list_workflow_templates_team(
                config.insforge_current_user_id,
                limit=limit,
            )
        else:
            if not config.insforge_current_user_id:
                raise typer.BadParameter("No current user is set. Run `tracker auth login` first.")
            templates = repository.list_workflow_templates_mine(
                config.insforge_current_user_id,
                limit=limit,
            )
        for template in templates:
            insight = repository.get_workflow_insight(template.session_id)
            setattr(template, "automation_score", insight.automation_score if insight else "")
            records.append(template)
    _render_template_table(records)


@workflows_app.command("search")
def workflows_search(
    query: str,
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
    limit: int = typer.Option(10, help="Maximum workflows to display."),
    scope: str = typer.Option("mine", "--scope", help="Search scope: mine or team."),
) -> None:
    """Search privacy-safe workflow history."""
    config = _build_config(db_path, cloud_sync=True)
    repository = LocalSQLiteRepository(config.db_path)
    client = _maybe_client(config)
    normalized_scope = _validate_scope(scope)
    if client:
        matches = client.search_workflows(query, limit=limit, scope=normalized_scope)
        template_ids = [match.get("template_id") for match in matches if match.get("template_id")]
        templates = [client.get_workflow_template(str(template_id)) for template_id in template_ids]
        records = [SimpleNamespace(**template) for template in templates if template]
    else:
        if normalized_scope == "team":
            records = repository.search_workflow_templates_team(
                query,
                user_id=config.insforge_current_user_id,
                limit=limit,
            )
        else:
            if not config.insforge_current_user_id:
                raise typer.BadParameter("No current user is set. Run `tracker auth login` first.")
            records = repository.search_workflow_templates_mine(
                query,
                user_id=config.insforge_current_user_id,
                limit=limit,
            )
    _render_template_table(records)


@workflows_app.command("show")
def workflows_show(
    workflow_id: str,
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
) -> None:
    """Show a workflow template, pseudocode, and insight details."""
    config = _build_config(db_path)
    repository = LocalSQLiteRepository(config.db_path)
    template = repository.get_workflow_template(workflow_id)
    if template is None:
        raise typer.BadParameter(f"No workflow template found for id {workflow_id}.")
    insight = repository.get_workflow_insight(template.session_id)
    console.print(Panel.fit(template.plain_text, title=template.title))
    if insight:
        console.print(
            Panel.fit(
                (
                    f"Summary: {insight.summary}\n"
                    f"Automation Score: {insight.automation_score}\n"
                    f"Reason: {insight.automation_reason}\n"
                    f"Next Action: {insight.recommended_next_action}\n"
                    f"Tags: {', '.join(insight.tags)}"
                ),
                title="Workflow Insight",
            )
        )


@workflows_app.command("templates")
def workflows_templates(
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
    limit: int = typer.Option(10, help="Maximum templates to display."),
) -> None:
    """List reusable workflow templates."""
    config = _build_config(db_path)
    repository = LocalSQLiteRepository(config.db_path)
    _render_template_table(repository.list_workflow_templates(limit=limit))


@workflows_app.command("insights")
def workflows_insights(
    session_id: str = typer.Option(..., help="Session ID to inspect."),
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
) -> None:
    """Generate or display workflow insight for a session."""
    config = _build_config(db_path, cloud_sync=True)
    repository = LocalSQLiteRepository(config.db_path)
    insight = repository.get_workflow_insight(session_id)
    if insight is None:
        insight, _template, _search_record, _handoff = _generate_workflow_outputs(
            config,
            repository,
            session_id,
        )
    console.print(
        Panel.fit(
            (
                f"Summary: {insight.summary}\n"
                f"Main Apps: {', '.join(insight.main_apps)}\n"
                f"Task Type: {insight.detected_task_type}\n"
                f"Automation Score: {insight.automation_score}\n"
                f"Reason: {insight.automation_reason}\n"
                f"Next Action: {insight.recommended_next_action}"
            ),
            title=f"Workflow Insight {session_id}",
        )
    )


@workflows_app.command("handoff")
def workflows_handoff(
    session_id: str = typer.Option(..., help="Session ID to inspect."),
    db_path: Optional[str] = typer.Option(None, help="Path to local SQLite DB."),
) -> None:
    """Create or display a review-only agent handoff draft."""
    config = _build_config(db_path, cloud_sync=True)
    repository = LocalSQLiteRepository(config.db_path)
    draft = repository.get_agent_handoff_draft(session_id)
    if draft is None:
        _insight, _template, _search_record, draft = _generate_workflow_outputs(
            config,
            repository,
            session_id,
        )
    if draft is None:
        console.print("No handoff draft generated. Automation score is below threshold.")
        return
    console.print(
        Panel.fit(
            (
                f"Status: {draft.status}\n"
                f"Requires Approval: {draft.requires_user_approval}\n"
                f"Proposed Action: {draft.proposed_action}\n"
                f"Action Plan:\n- " + "\n- ".join(draft.action_plan)
            ),
            title=f"Agent Handoff Draft {session_id}",
        )
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
