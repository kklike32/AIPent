# AGENTS.md

This file is the quick operator guide for contributors and coding agents working in this repository.

## Project Summary

- Project: `computer-usage-tracker` (Python, local-first desktop tracker)
- Entry point: `tracker` CLI (implemented in `src/tracker/cli.py`)
- Python requirement: `>=3.11`
- Local storage: SQLite at `data/local_tracker.db` by default
- Optional backend: InsForge cloud (sessions, events, screenshots, summaries)

## Local Setup (Recommended)

1. Create and activate a virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

1. Install dependencies:

```bash
python -m pip install -e '.[dev]'
```

1. Create local environment config:

```bash
cp .env.example .env
```

1. Run tests:

```bash
python -m pytest -q
```

## Runtime Configuration

The app reads environment from `.env` (not `.env.local`).

Required for cloud sync:

- `INSFORGE_BASE_URL`
- `INSFORGE_PROJECT_ID`
- `INSFORGE_API_KEY`
- `ENABLE_CLOUD_SYNC=true`

Optional:

- `INSFORGE_AUTH_TOKEN`
- `INSFORGE_STORAGE_BUCKET` (defaults to `session-screenshots`)
- `ENABLE_SCREENSHOT_UPLOAD=true` to upload screenshot files
- `LOCAL_DB_PATH` to override local SQLite path

Notes:

- `.env` is gitignored. Never commit secrets.
- If `ENABLE_CLOUD_SYNC=false`, data remains local only.

## Core CLI Workflow

Use these commands from the activated venv:

```bash
python -m tracker.cli --help
python -m tracker.cli start
python -m tracker.cli stop
python -m tracker.cli summarize
python -m tracker.cli export --session-id <session_id>
python -m tracker.cli sync
```

`start` collects session, window, keyboard, mouse, screenshot, and OCR events. `summarize` produces pseudocode and suggestions. `sync` pushes unsynced rows to InsForge.

## Codebase Map

- `src/tracker/cli.py`: CLI entrypoints and orchestration
- `src/tracker/recorder.py`: live input/window/screenshot event capture loop
- `src/tracker/events.py`: event/session/screenshot/summary models and event types
- `src/tracker/storage/local_sqlite.py`: local persistence and sync flags
- `src/tracker/storage/insforge_client.py`: InsForge HTTP API integration
- `src/tracker/sync.py`: sync engine for sessions/events/screenshots/summaries
- `src/tracker/pseudocode.py`: deterministic pseudocode generation
- `src/tracker/suggestions.py`: deterministic suggestion generation
- `tests/`: unit tests

## Data Correlation Rules

- Every event is tied to `session_id`.
- Screenshot records are tied to both `session_id` and screenshot event `event_id`.
- Ordering is timestamp-based in local storage and during sync.
- Sync marks each row with `synced` and optional remote identifiers.

## InsForge API Expectations

Current Python client uses project API routes:

- Database insert: `/api/database/records/<table>`
- Storage upload strategy: `/api/storage/buckets/<bucket>/upload-strategy`
- Storage upload flow: presigned upload and optional confirm URL

If sync fails with 404, verify base URL, API key, and route compatibility first.

<!-- INSFORGE:START -->
## InsForge backend

This project uses [InsForge](https://insforge.dev): an all-in-one, open-source Postgres-based backend (BaaS) that gives this app a database, authentication, file storage, edge functions, realtime, an AI model gateway, and payments through one platform.

- **Project:** **insforge-hackathon** (API base `https://r34ir5jz.us-east.insforge.app`)
- **Skills:** these InsForge skills are installed for supported coding agents. Reach for them before implementing any InsForge feature instead of guessing the API:
  - `insforge`: app code with the `@insforge/sdk` client (database CRUD, auth, storage, edge functions, realtime, AI, email, and Stripe payments).
  - `insforge-cli`: backend and infrastructure via the `insforge` CLI (projects, SQL, migrations, RLS policies, storage buckets, functions, secrets, payment setup, schedules, deploys).
  - `insforge-debug`: diagnosing failures (SDK/HTTP errors, RLS denials, auth and OAuth issues) and running security or performance audits.
  - `insforge-integrations`: wiring external auth providers (Clerk, Auth0, WorkOS, Better Auth, etc.) for JWT-based RLS, or the OKX x402 payment facilitator.
  - `find-skills`: discovering additional skills on demand.
- **Credentials:** app code reads keys from `.env.local`; the CLI reads `.insforge/project.json`. Never hardcode or commit keys.

Key patterns:

- Database inserts take an array: `insert([{ ... }])`.
- Reference users with `auth.users(id)`; use `auth.uid()` in RLS policies.
- For storage uploads, persist both the returned `url` and `key`.
<!-- INSFORGE:END -->

## Troubleshooting

1. `ImportError` for `StrEnum`:
- Use Python 3.11+ (3.10 is unsupported).

1. Cloud sync fails with 404:
- Check `INSFORGE_BASE_URL` and API route assumptions in `insforge_client.py`.

1. Cloud sync fails with auth errors:
- Verify `INSFORGE_API_KEY` and optional `INSFORGE_AUTH_TOKEN`.

1. Screenshot upload times out:
- Confirm storage bucket exists and upload strategy/confirm flow succeeds.

1. No keyboard or mouse events recorded:
- Ensure macOS accessibility/input monitoring permissions are granted.

## Commit Guidance

- Keep commits focused and small.
- Do not commit `.env` or local DB artifacts.
- Run `python -m pytest -q` before pushing behavioral changes.
