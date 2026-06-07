# BuddyBar

`BuddyBar` is a lightweight macOS menubar app for the tracker in this repository.

It launches the existing capture pipeline from the top bar, shows live status, and lets you:

- start screen capture
- stop capture and save the session
- open the local data and export folders
- reveal the project root quickly

## Run

From this folder:

```bash
swift run
```

The app expects the tracker repo root to be one level above `macos/`, with:

- `.venv/bin/python`
- `.env`
- `src/tracker`

Optional overrides:

- `TRACKER_PROJECT_ROOT`
- `TRACKER_PYTHON_EXECUTABLE`

## Notes

- The first launch needs macOS Screen Recording and Accessibility permissions.
- The current Swift app is a native macOS shell around the existing tracker pipeline, so capture still uses the repo's Python backend.
