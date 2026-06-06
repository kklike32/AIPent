from __future__ import annotations

import platform
import subprocess


def _macos_frontmost_app_and_window() -> tuple[str | None, str | None]:
    script = """
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
        tell process frontApp
            try
                set winTitle to name of front window
            on error
                set winTitle to ""
            end try
        end tell
    end tell
    return frontApp & "||" & winTitle
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=True,
        )
        raw = result.stdout.strip()
        if "||" in raw:
            app_name, window_title = raw.split("||", maxsplit=1)
            return app_name or None, window_title or None
    except Exception:
        return None, None
    return None, None


def _pygetwindow_fallback() -> tuple[str | None, str | None]:
    try:
        import pygetwindow as gw

        active = gw.getActiveWindow()
        if not active:
            return None, None
        return None, getattr(active, "title", None)
    except Exception:
        return None, None


def get_active_app_context() -> tuple[str | None, str | None]:
    system = platform.system()
    if system == "Darwin":
        app_name, window_title = _macos_frontmost_app_and_window()
        if app_name or window_title:
            return app_name, window_title

    # TODO: Add richer Linux/Windows active app + process resolution.
    return _pygetwindow_fallback()
