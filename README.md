# computer-usage-tracker

`computer-usage-tracker` is a local-first Python desktop prototype that captures computer activity, summarizes short activity windows with an LLM, and produces a final pseudocode workflow for the full session.

InsForge is the privacy-safe workflow intelligence backend. The desktop app keeps raw activity local, while InsForge stores the useful, safe, structured workflow knowledge: summaries, pseudocode, templates, tags, automation scores, and agent handoff plans.

## Architecture

Core flow:

- local screenshots every 2 seconds
- local mouse, keyboard, app/window, and OCR capture
- 6-second chunk builder
- LLM chunk summarization
- local summary persistence
- final session pseudocode generation
- workflow insight generation
- reusable workflow template generation
- privacy-safe workflow search indexing
- automation-readiness scoring
- draft agent handoff planning
- privacy-safe InsForge sync for structured workflow records only

Relevant modules:

- `tracker.recorder`: session lifecycle, capture loop, chunk summarization, finalization
- `tracker.chunker`: in-memory 6-second chunk assembly
- `tracker.llm`: provider abstraction, mock provider, Vertex Gemini provider
- `tracker.summarization`: prompt-safe orchestration helpers
- `tracker.workflows`: deterministic workflow insight, scoring, template, search, and handoff logic
- `tracker.storage.local_sqlite`: local persistence for raw data and workflow outputs
- `tracker.storage.insforge_client`: InsForge API wrapper for privacy-safe workflow records
- `tracker.sync`: workflow intelligence sync service

## Privacy-First Backend Design

- Raw data stays local in SQLite and the local screenshot directory.
- Raw screenshots, OCR text, mouse clicks, keyboard logs, and app/window activity are purged locally after the retention window. Default: 300 seconds after capture.
- Screenshots are used only transiently for local chunk summarization.
- Gemini / Vertex may receive screenshots and local context for model analysis.
- InsForge receives only session metadata, detailed chunk summaries, final pseudocode, workflow tags, workflow templates, automation scores, suggested next actions, and draft agent handoff plans.
- InsForge never receives screenshots, raw mouse coordinates, raw keyboard events, full OCR text, local event logs, or raw app/window streams.
- Users can disable cloud sync with `ENABLE_CLOUD_SYNC=false` or `tracker start --no-cloud-sync`.
- Users can switch away from Vertex/Gemini by implementing the `LLMClient` interface and selecting another provider.

## Why InsForge Matters

InsForge is not just used as a database. It is the backend that turns private desktop activity into reusable organizational workflow knowledge.

The local app captures sensitive raw activity, but only safe summaries and pseudocode are synced to InsForge. This allows teams to build a searchable workflow library without uploading screenshots, keystrokes, or raw user activity.

With InsForge, the app can:
- remember previous workflows
- search completed sessions
- create reusable workflow templates
- score which workflows are good candidates for automation
- share safe workflow documentation across a team
- prepare approved workflows for future agent execution

## InsForge Auth and Skill Ownership

The project reuses the existing InsForge authentication setup from the shared frontend application.

Every synced workflow record is associated with an authenticated InsForge user. This lets the
system track who created each workflow, who owns each repeatable skill, and which skills are
private versus shared with the team.

Raw desktop data is never uploaded. Auth only applies to safe backend records:

- chunk summaries
- final pseudocode
- workflow insights
- workflow templates
- search index records
- agent handoff drafts

Default visibility is private. Users can explicitly publish a skill template to the team library.

## Sharing Model

Private:

- session metadata
- chunk summaries
- final pseudocode
- workflow insights
- agent handoff drafts
- visible only to creator

Team:

- workflow template
- search index record
- title, description, tags, pseudocode, automation score
- visible to authenticated users in the project/team

Never shared:

- screenshots
- raw OCR
- raw keyboard events
- raw mouse events
- raw local activity logs

## Setup

### Requirements

- Python 3.11+
- Tesseract OCR installed locally
  - macOS: `brew install tesseract`

### Install

```bash
python -m pip install -e .[dev]
python -m pip install -e .[vertex]
```

Install the `vertex` extra only when using `tracker start --llm-provider vertex_gemini`.

### Desktop App

Run the Tauri desktop app from the terminal with these steps:

```bash
cd desktop
npm install
unset NODE_OPTIONS
source "$HOME/.cargo/env"
npm run tauri dev
```

If you only want the frontend during development, use:

```bash
cd desktop
npm run dev
```

Stop the desktop app with `Ctrl+C` in the terminal.

### Environment

Copy `.env.example` to `.env`.

Key variables:

```bash
SCREENSHOT_INTERVAL_SECONDS=2
CHUNK_INTERVAL_SECONDS=6
RAW_DATA_TTL_SECONDS=300
ENABLE_CLOUD_SYNC=false
ENABLE_WORKFLOW_TEMPLATE_CREATION=true
ENABLE_WORKFLOW_INSIGHTS=true
ENABLE_AGENT_HANDOFF_DRAFTS=true
AGENT_HANDOFF_AUTOMATION_SCORE_THRESHOLD=75
LLM_PROVIDER=vertex_gemini
LLM_MODEL=gemini-1.5-pro
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=
INSFORGE_BASE_URL=
INSFORGE_PROJECT_ID=
INSFORGE_API_KEY=
INSFORGE_AUTH_ENABLED=true
INSFORGE_AUTH_TOKEN=
INSFORGE_CURRENT_USER_ID=
DEFAULT_WORKFLOW_VISIBILITY=private
ENABLE_TEAM_SHARING=true
INSFORGE_SUMMARIES_TABLE=chunk_summaries
INSFORGE_FINAL_TABLE=final_pseudocode
INSFORGE_WORKFLOW_TEMPLATES_TABLE=workflow_templates
INSFORGE_WORKFLOW_INSIGHTS_TABLE=workflow_insights
INSFORGE_AGENT_HANDOFF_TABLE=agent_handoff_queue
INSFORGE_WORKFLOW_SEARCH_TABLE=workflow_search_index
LOCAL_DB_PATH=data/local_tracker.db
```

## CLI

Initialize backend artifacts:

```bash
tracker init-backend
```

Start tracking:

```bash
tracker start --llm-provider mock
tracker start --cloud-sync --llm-provider vertex_gemini
tracker start --cloud-sync --visibility private
tracker start --cloud-sync --visibility team
```

Generate final pseudocode from stored chunk summaries:

```bash
tracker summarize-final --session-id <session_id>
```

Sync privacy-safe workflow records:

```bash
tracker sync-summaries --session-id <session_id>
tracker sync

tracker auth login
tracker auth status
tracker auth logout
```

Workflow intelligence commands:

```bash
tracker workflows list --mine
tracker workflows list --team
tracker workflows search "excel chart" --scope mine
tracker workflows search "excel chart" --scope team
tracker workflows show <workflow_id>
tracker workflows templates
tracker workflows insights --session-id <session_id>
tracker workflows handoff --session-id <session_id>
```

Export final pseudocode:

```bash
tracker export --session-id <session_id>
```

### Terminal Workflow Summary

If you want the full terminal-driven flow without the desktop UI, use:

```bash
python -m pip install -e .[dev]
python -m pip install -e .[vertex]
cp .env.example .env
tracker init-backend
tracker start --llm-provider mock
tracker start --cloud-sync --llm-provider vertex_gemini
tracker summarize-final --session-id <session_id>
tracker sync
tracker export --session-id <session_id>
```

For the desktop UI flow, use the desktop commands above and then run the recorder from the app.

## Remote Schema

InsForge stores only these tables:

- `sessions`
- `chunk_summaries`
- `final_pseudocode`
- `workflow_templates`
- `workflow_insights`
- `agent_handoff_queue`
- `workflow_search_index`

Local SQLite stores:

- raw transient activity data in `events` and `screenshots`
- chunk summaries in `chunk_summaries`
- final workflow output in `final_pseudocode`
- workflow intelligence artifacts for sync and demo queries

Do not add or sync tables for raw screenshots, keyboard logs, mouse logs, OCR logs, or raw events.

Use [`insforge_schema.sql`](/Users/keenan/Documents/AIPent/insforge_schema.sql) to create the backend tables.

## InsForge-Powered Demo Features

This project uses InsForge as the workflow intelligence backend.

During the demo, we can show:

1. A local desktop tracker captures private activity.
2. Every 6 seconds, the app creates a safe natural-language summary.
3. Only summaries and workflow outputs are synced to InsForge.
4. InsForge stores the workflow memory.
5. The user can search previous workflows.
6. The app converts sessions into reusable workflow templates.
7. InsForge stores automation-readiness scores.
8. High-scoring workflows create draft agent handoff plans.
9. No screenshots, raw keystrokes, mouse coordinates, or OCR text are uploaded.

This makes InsForge the backend for privacy-safe workflow memory, search, templates, and future automation.

## Hackathon Demo Script

1. Start a session:
   `tracker start --cloud-sync --llm-provider vertex_gemini`
2. Perform a short workflow:
   Example: open a spreadsheet, select data, create a chart, rename it, and save/export.
3. Stop the session.
4. Show that raw data stayed local:
   - screenshots are stored only locally
   - raw events are stored only locally
   - InsForge contains no raw screenshots or keystrokes
5. Show InsForge records:
   - session metadata
   - chunk summaries
   - final pseudocode
   - workflow insight
   - workflow template
   - automation score
   - agent handoff draft
6. Search previous workflows:
   `tracker workflows search "spreadsheet chart"`
7. Show reusable workflow template:
   `tracker workflows templates`
8. Show agent handoff draft:
   `tracker workflows handoff --session-id <session_id>`
9. End with:
   “InsForge turns private desktop activity into safe, searchable, reusable workflow knowledge that can later power approved agent automation.”

## Tests

```bash
python -m pytest -q
```
