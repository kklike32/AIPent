from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from .config import TrackerConfig
from .events import Event, EventType
from .pseudocode import PseudocodeGenerator
from .recorder import SessionRecorder
from .storage import SQLiteStorage
from .suggestions import SuggestionEngine

app = typer.Typer(help="Track desktop usage sessions and summarize workflows.")
console = Console()


def _build_config(
    db_path: str | None,
    screenshot_interval: int | None,
    ocr: bool | None,
    local_only: bool | None,
) -> TrackerConfig:
    config = TrackerConfig()
    if db_path:
        config.db_path = Path(db_path)
    if screenshot_interval is not None:
        config.screenshot_interval_seconds = screenshot_interval
    if ocr is not None:
        config.ocr_enabled = ocr
    if local_only is not None:
        config.local_only_mode = local_only
    config.ensure_directories()
    return config


def _get_session_id(storage: SQLiteStorage, session_id: int | None) -> int:
    chosen = session_id or storage.get_latest_session_id()
    if chosen is None:
        raise typer.BadParameter("No sessions found.")
    return chosen


@app.command()
def start(
    db_path: str | None = typer.Option(None, help="Path to local SQLite DB."),
    screenshot_interval: int = typer.Option(
        5,
        min=1,
        help="Screenshot interval in seconds.",
    ),
    ocr: bool = typer.Option(True, "--ocr/--no-ocr", help="Toggle OCR."),
    local_only: bool = typer.Option(
        True,
        "--local-only/--allow-remote",
        help="Local-only mode for this prototype.",
    ),
) -> None:
    """Start a new tracking session and record until Ctrl+C."""
    config = _build_config(db_path, screenshot_interval, ocr, local_only)
    storage = SQLiteStorage(config.db_path)
    recorder = SessionRecorder(config, storage)

    console.print("[bold green]Tracking started.[/bold green] Press Ctrl+C to stop.")
    session_id = recorder.run()
    console.print(f"[bold]Session stopped:[/bold] {session_id}")


@app.command()
def stop(
    session_id: int | None = typer.Option(None, help="Session ID to stop."),
    db_path: str | None = typer.Option(None, help="Path to local SQLite DB."),
) -> None:
    """Stop a running session by ID (best effort)."""
    config = _build_config(db_path, None, None, None)
    storage = SQLiteStorage(config.db_path)
    target_session_id = session_id or storage.get_active_session_id()

    if target_session_id is None:
        console.print("[yellow]No running session found.[/yellow]")
        raise typer.Exit(0)

    storage.add_event(
        Event(
            session_id=target_session_id,
            event_type=EventType.SESSION_STOP,
            metadata={"reason": "manual_stop_command"},
        )
    )
    storage.stop_session(target_session_id)
    console.print(f"[bold]Marked session as stopped:[/bold] {target_session_id}")


@app.command()
def summarize(
    session_id: int | None = typer.Option(None, help="Session ID to summarize."),
    db_path: str | None = typer.Option(None, help="Path to local SQLite DB."),
) -> None:
    """Summarize a session into pseudocode and suggestions."""
    config = _build_config(db_path, None, None, None)
    storage = SQLiteStorage(config.db_path)
    chosen_session_id = _get_session_id(storage, session_id)

    events = storage.get_events(chosen_session_id)
    pseudocode = PseudocodeGenerator().generate(events)
    suggestions = SuggestionEngine().suggest(events, pseudocode)

    console.print(Panel.fit(pseudocode, title=f"Session {chosen_session_id} Pseudocode"))
    suggestion_text = "\n".join(
        f"Suggestion {idx}: {suggestion}"
        for idx, suggestion in enumerate(suggestions, start=1)
    )
    console.print(Panel.fit(suggestion_text, title="Suggestions"))


@app.command()
def export(
    session_id: int = typer.Option(..., help="Session ID to export."),
    format: str = typer.Option("markdown", help="Export format."),
    db_path: str | None = typer.Option(None, help="Path to local SQLite DB."),
    output: str | None = typer.Option(None, help="Output path override."),
) -> None:
    """Export session summary to markdown."""
    config = _build_config(db_path, None, None, None)
    storage = SQLiteStorage(config.db_path)

    if format.lower() != "markdown":
        raise typer.BadParameter("Only markdown export is supported in this prototype.")

    events = storage.get_events(session_id)
    pseudocode = PseudocodeGenerator().generate(events)
    suggestions = SuggestionEngine().suggest(events, pseudocode)

    if output:
        output_path = Path(output)
    else:
        output_path = config.export_dir / f"session_{session_id}_summary.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    suggestion_lines = "\n".join(
        f"- Suggestion {idx}: {text}" for idx, text in enumerate(suggestions, start=1)
    )
    markdown = (
        f"# Session {session_id} Summary\n\n"
        f"## Pseudocode\n\n{pseudocode}\n\n"
        f"## Suggestions\n\n{suggestion_lines}\n"
    )
    output_path.write_text(markdown, encoding="utf-8")
    console.print(f"[bold green]Exported:[/bold green] {output_path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
