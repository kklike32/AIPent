# computer-usage-tracker

A local-first Python prototype that tracks desktop activity during a work session, converts recorded actions into readable pseudocode, and suggests useful next steps.

## Important Privacy and Consent Notes

- This project is designed for personal use on your own machine.
- You are responsible for getting consent if any other user's data is visible on your system.
- By default, keyboard tracking records shortcuts only and does **not** log full typed text.
- The tracker attempts to avoid sensitive capture by skipping obvious password contexts.
- All data is stored locally in SQLite and local folders.

## Features

- Session-based tracking (`tracker start`, `tracker stop`)
- Event storage in local SQLite
- Mouse click capture
- Keyboard shortcut capture (not raw key logging)
- Active app/window snapshots
- Periodic screenshots
- Optional OCR extraction from screenshots
- Rule-based pseudocode generation
- Rule-based workflow suggestions
- Markdown export for session summaries
- Placeholder `ActionAgent` interface for future user-approved automation

## Architecture Overview

- `tracker.recorder`: session loop, keyboard/mouse listeners, screenshot loop, pause/resume
- `tracker.storage`: SQLite schema and persistence
- `tracker.events`: event models and event types
- `tracker.app_context`: active app/window detection
- `tracker.screenshot` + `tracker.ocr`: screenshot capture and OCR pipeline
- `tracker.pseudocode`: deterministic pseudocode generation (`PseudocodeGenerator`)
- `tracker.suggestions`: deterministic suggestion engine (`SuggestionEngine`)
- `tracker.agent`: placeholder for future action-execution agent

## Setup

### Requirements

- Python 3.11+
- Tesseract OCR installed on your machine for OCR support:
  - macOS (Homebrew): `brew install tesseract`

### Install

```bash
pip install -e .
```

For development tools:

```bash
pip install -e .[dev]
```

## Usage

Start a tracking session:

```bash
tracker start
```

Behavior:

- Creates a new session in local SQLite.
- Runs until interrupted with `Ctrl+C`.
- Saves screenshots in `data/screenshots/`.
- Saves OCR events (if enabled) and context events.

Stop an active session by ID:

```bash
tracker stop --session-id <id>
```

Summarize latest session:

```bash
tracker summarize
```

Summarize a specific session:

```bash
tracker summarize --session-id <id>
```

Export a summary to Markdown:

```bash
tracker export --session-id <id> --format markdown
```

## Privacy Controls

- Shortcut-only keyboard capture by default (no raw typing stream)
- Sensitive-context filtering for password-like windows and OCR text
- Pause/resume tracking while running using `Ctrl+Shift+P`
- Local-only mode enabled by default
- OCR toggle enabled by default and configurable

## Configuration

Runtime defaults are in `src/tracker/config.py`:

- Screenshot interval: 5 seconds
- OCR enabled: true
- Local-only mode: true
- Database path: `data/tracker.sqlite3`

## Tests

Run tests:

```bash
pytest
```

Current tests cover:

- Event creation
- SQLite storage
- Pseudocode generation
- Suggestion generation

## Roadmap

- LLM-backed pseudocode/suggestion adapters (OpenAI/Ollama/local)
- Stronger app/window detection across OSes
- Better redaction and privacy policies
- Session replay and template extraction
- User-confirmed action execution agent (future)
