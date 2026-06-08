# AIPent

**AIPent is a native macOS menubar app for turning real desktop work into reusable workflow knowledge.**

It lives in the menu bar, starts recording in one click, keeps raw activity local, and produces a clean workflow preview you can review before syncing approved summaries to [InsForge](https://insforge.dev).

![Platform](https://img.shields.io/badge/platform-macOS-black)
![Backend](https://img.shields.io/badge/backend-InsForge-0f766e)
![Privacy](https://img.shields.io/badge/mode-local--first-1d4ed8)

## Why AIPent Feels Different

Most activity trackers behave like developer tools. AIPent is designed more like a product:

- **Native macOS menubar experience.** Start and stop capture without living in a terminal.
- **Review before sync.** BuddyBar shows a generated steps preview before anything is sent to the cloud.
- **Local-first by default.** Screenshots, OCR text, keyboard events, and mouse activity stay on your machine.
- **Structured output, not raw surveillance.** The end result is workflow summaries, pseudocode, reusable templates, and automation hints.
- **Built for real knowledge capture.** The goal is not analytics dashboards. The goal is to preserve how work actually gets done.

## The Main Product: BuddyBar

`BuddyBar` is the primary experience in this repo: a lightweight native macOS menubar app located in [`macos/BuddyBar`](/Users/keenan/Documents/AIPent/macos/BuddyBar).

From the menu bar, BuddyBar lets you:

- start a capture session
- stop and save the session
- see live session state and the latest log line
- preview generated workflow steps after capture ends
- sync the approved session summary to InsForge
- open the local data folder and exports folder
- reveal the project root quickly

The current implementation uses the Python tracking engine underneath, but the day-to-day experience is intentionally macOS-first.

## How It Works

1. You start a session from BuddyBar.
2. The local tracker records screenshots, app/window context, and event metadata on-device.
3. The recorder groups activity into short chunks and generates workflow summaries.
4. When the session stops, AIPent creates a final pseudocode-style workflow preview.
5. You review the result in BuddyBar.
6. If you want cloud memory and search, you sync the approved privacy-safe summary to InsForge.

## Privacy Model

What stays local:

- screenshots
- raw OCR text
- keyboard and mouse activity
- local event logs
- the SQLite capture database

What can be synced to InsForge:

- session metadata
- chunk summaries
- final pseudocode
- workflow insights
- reusable workflow templates
- workflow search records
- draft agent handoff records

This is the core product idea: capture sensitive work locally, then sync only the useful structured workflow knowledge.

## InsForge

[InsForge](https://insforge.dev) is the backend used for privacy-safe workflow memory, search, and sharing.

When connected, AIPent can use InsForge to:

- keep approved workflow summaries off-device
- store reusable workflow templates
- search previous workflows
- prepare handoff-ready structured outputs for later automation

For BuddyBar, sync is explicit. The app records locally first, then offers a deliberate "sync preview" action after the workflow has been generated.

## Quick Start

### 1. Set up the Python runtime

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

If you want Gemini / Vertex-powered summarization, also install:

```bash
python -m pip install -e '.[vertex]'
```

### 2. Install local dependencies

```bash
brew install tesseract
```

### 3. Create your environment file

```bash
cp .env.example .env
```

BuddyBar expects the repo root to contain:

- `.venv/bin/python`
- `.env`
- `src/tracker`

### 4. Launch the native macOS app

```bash
cd macos/BuddyBar
swift run
```

On first launch, macOS will require **Screen Recording** and **Accessibility** permissions.

## Using BuddyBar

### Local-only workflow

This is the default and recommended way to get started:

1. Launch BuddyBar.
2. Click **Start** in the menu bar panel.
3. Do the task you want to capture.
4. Click **Stop**.
5. Review the generated steps preview in BuddyBar.
6. Open the exports or data folder if you want to inspect local artifacts.

### Syncing a reviewed workflow to InsForge

Add these values to `.env`:

```bash
INSFORGE_BASE_URL=
INSFORGE_PROJECT_ID=
INSFORGE_API_KEY=
INSFORGE_AUTH_TOKEN=
INSFORGE_CURRENT_USER_ID=
```

Then, after a session is complete, use the **Sync Preview to InsForge** button in BuddyBar.

If you want to validate the saved auth token from the command line, you can also use:

```bash
python -m tracker.cli auth status
```

## Command Line Usage

The menu bar app is the best product surface, but the tracker engine is also available as a CLI.

Start a session:

```bash
python -m tracker.cli start
```

Start a session with explicit cloud sync enabled:

```bash
python -m tracker.cli start --cloud-sync --visibility private
```

Generate a final workflow summary:

```bash
python -m tracker.cli summarize
```

Export a session:

```bash
python -m tracker.cli export --session-id <session_id>
```

Sync unsynced records:

```bash
python -m tracker.cli sync
```

## Desktop Dashboard

There is also a Tauri-based desktop dashboard in [`desktop`](/Users/keenan/Documents/AIPent/desktop). It provides a larger control panel for recording state, pipeline progress, chunk summaries, privacy settings, and final workflow output.

Run it with:

```bash
cd desktop
npm install
source "$HOME/.cargo/env"
unset NODE_OPTIONS
npm run tauri dev
```

The dashboard is useful during development, but the repo’s most product-like user experience today is the native BuddyBar menubar app.

## Project Layout

- [`macos/BuddyBar`](/Users/keenan/Documents/AIPent/macos/BuddyBar) - native macOS menubar app
- [`desktop`](/Users/keenan/Documents/AIPent/desktop) - Tauri desktop dashboard
- [`src/tracker/cli.py`](/Users/keenan/Documents/AIPent/src/tracker/cli.py) - CLI entrypoint
- [`src/tracker/recorder.py`](/Users/keenan/Documents/AIPent/src/tracker/recorder.py) - capture loop and session orchestration
- [`src/tracker/storage/local_sqlite.py`](/Users/keenan/Documents/AIPent/src/tracker/storage/local_sqlite.py) - local persistence
- [`src/tracker/storage/insforge_client.py`](/Users/keenan/Documents/AIPent/src/tracker/storage/insforge_client.py) - InsForge client
- [`insforge_schema.sql`](/Users/keenan/Documents/AIPent/insforge_schema.sql) - backend schema reference

## Product Positioning

AIPent is best understood as a workflow capture product for macOS:

- **BuddyBar** makes capture feel lightweight and always available.
- **The local tracker** turns activity into structured workflow knowledge.
- **InsForge** becomes the searchable memory layer for approved outputs.

That combination is what makes the project compelling: native capture on the Mac, careful privacy boundaries, and a backend designed for reusable workflow intelligence instead of raw activity dumping.
