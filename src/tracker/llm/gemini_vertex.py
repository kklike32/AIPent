from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from tracker.config import TrackerConfig
from tracker.events import ActivityChunk, ChunkSummary, FinalPseudocode

from .base import LLMClient

CHUNK_SUMMARY_PROMPT = """You are analyzing a short 6-second computer usage window.

Inputs may include:
- 3 screenshots captured every 2 seconds
- active application names
- active window titles
- mouse click events
- keyboard shortcuts
- OCR text extracted locally

Task:
Write a concrete, descriptive summary of what the user appears to be doing in this window.

Rules:
- Write 2-4 sentences in plain English.
- Describe the visible workflow in chronological order.
- Name the application, website, document, tab, panel, dialog, button, menu, field, link, or item being interacted with when you can infer it from the screenshots, window titles, OCR text, or event sequence.
- Explicitly mention notable user actions such as opening, switching, selecting, clicking, typing, pasting, submitting, dragging, scrolling, confirming, or exporting when supported by the evidence.
- Mention what likely changed on screen after the action when visible, such as a modal opening, a form updating, a selection changing, a page loading, or a result appearing.
- If there are clicks or shortcuts but the exact target is unclear, say what the user likely clicked or invoked and why it is uncertain.
- Prefer specific action verbs over generic phrasing like "worked on" or "interacted with".
- Do not include raw mouse coordinates.
- Do not include raw keyboard logs.
- Do not include sensitive text unless it is essential and clearly visible.
- Do not mention screenshots, OCR, or "the image shows".
- Prefer describing intent and workflow.
- Mention the application or website when clear.
- Mention uncertainty when the action is ambiguous.
- Focus on what happened during this 6-second window.

Return JSON:
{
  "summary": "...",
  "observed_apps": ["..."],
  "confidence": "high | medium | low"
}
"""

FINAL_PSEUDOCODE_PROMPT = """You are given a sequence of detailed summaries from a recorded computer session.

Task:
Convert the full session into a clean pseudocode-style workflow.

Rules:
- Combine repeated low-level actions into meaningful workflow steps.
- Do not mention screenshots, mouse coordinates, or raw keyboard events.
- Prefer clear action verbs.
- Preserve chronological order.
- Include enough detail that a user could understand or recreate the workflow.
- If the workflow appears automatable, include suggestions.

Return JSON:
{
  "pseudocode": [
    "Step 1...",
    "Step 2..."
  ],
  "plain_text": "1. ...\\n2. ...",
  "suggestions": [
    "..."
  ]
}
"""


class VertexGeminiClient(LLMClient):
    def __init__(self, config: TrackerConfig) -> None:
        self.config = config
        self._api_key = (
            config.vertex_api_key
            or config.google_api_key
            or config.gemini_api_key
            or os.getenv("VERTEX_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        if config.google_application_credentials:
            os.environ.setdefault(
                "GOOGLE_APPLICATION_CREDENTIALS",
                config.google_application_credentials,
            )

        self._mode = "api_key" if self._api_key else "vertex_sdk"
        if self._mode == "vertex_sdk":
            try:
                import vertexai
                from vertexai.generative_models import GenerativeModel, Image, Part
            except ImportError as exc:
                raise RuntimeError(
                    "Vertex Gemini support requires either an API key or the `vertex` optional dependencies."
                ) from exc

            vertexai.init(
                project=config.google_cloud_project,
                location=config.google_cloud_location,
            )
            self._model = GenerativeModel(config.llm_model)
            self._image_cls = Image
            self._part_cls = Part

    def summarize_chunk(self, chunk: ActivityChunk) -> ChunkSummary:
        structured_context = self._build_chunk_context(chunk)
        if self._mode == "api_key":
            payload = self._generate_content_api_key(
                CHUNK_SUMMARY_PROMPT,
                structured_context,
                chunk.screenshots,
            )
        else:
            parts = [CHUNK_SUMMARY_PROMPT, json.dumps(structured_context, indent=2)]
            parts.extend(self._image_part(path) for path in chunk.screenshots)
            response = self._model.generate_content(parts)
            payload = self._extract_json(response)
        return ChunkSummary(
            session_id=chunk.session_id,
            chunk_index=chunk.chunk_index,
            started_at=chunk.started_at,
            ended_at=chunk.ended_at,
            summary=str(payload["summary"]),
            observed_apps=[str(item) for item in payload.get("observed_apps", [])],
            confidence=str(payload["confidence"]),
        )

    def generate_final_pseudocode(self, summaries: list[ChunkSummary]) -> FinalPseudocode:
        if not summaries:
            raise ValueError("At least one chunk summary is required.")

        ordered = sorted(summaries, key=lambda summary: summary.chunk_index)
        summary_payload = [
            {
                "chunk_index": summary.chunk_index,
                "started_at": summary.started_at,
                "ended_at": summary.ended_at,
                "summary": summary.summary,
                "observed_apps": summary.observed_apps,
                "confidence": summary.confidence,
            }
            for summary in ordered
        ]
        if self._mode == "api_key":
            payload = self._generate_content_api_key(
                FINAL_PSEUDOCODE_PROMPT,
                summary_payload,
                [],
            )
        else:
            payload = self._extract_json(
                self._model.generate_content(
                    [
                        FINAL_PSEUDOCODE_PROMPT,
                        json.dumps(summary_payload, indent=2),
                    ]
                )
            )
        return FinalPseudocode(
            session_id=ordered[0].session_id,
            pseudocode=[str(item) for item in payload["pseudocode"]],
            plain_text=str(payload["plain_text"]),
            suggestions=[str(item) for item in payload.get("suggestions", [])],
        )

    def _image_part(self, path: Path):
        return self._part_cls.from_image(self._image_cls.load_from_file(str(path)))

    def _build_chunk_context(self, chunk: ActivityChunk) -> dict[str, object]:
        recent_windows = self._dedupe_preserve_order(
            [
                {
                    "app_name": item.get("app_name"),
                    "window_title": item.get("window_title"),
                }
                for item in chunk.active_windows
                if item.get("app_name") or item.get("window_title")
            ]
        )
        shortcuts = [
            str(event.get("shortcut"))
            for event in chunk.keyboard_shortcuts
            if event.get("shortcut")
        ]
        click_buttons = [
            str(event.get("button"))
            for event in chunk.mouse_events
            if event.get("button")
        ]
        ocr_snippets = [text.strip() for text in chunk.ocr_text if text.strip()]
        return {
            "session_id": chunk.session_id,
            "chunk_index": chunk.chunk_index,
            "started_at": chunk.started_at,
            "ended_at": chunk.ended_at,
            "interaction_hints": {
                "screenshot_count": len(chunk.screenshots),
                "mouse_click_count": len(chunk.mouse_events),
                "mouse_buttons": click_buttons,
                "keyboard_shortcut_count": len(shortcuts),
                "keyboard_shortcuts": shortcuts,
                "window_sequence": recent_windows,
                "ocr_snippets": ocr_snippets[:5],
            },
            "mouse_events": chunk.mouse_events,
            "keyboard_shortcuts": chunk.keyboard_shortcuts,
            "active_windows": chunk.active_windows,
            "ocr_text": chunk.ocr_text,
        }

    def _generate_content_api_key(
        self,
        prompt: str,
        payload: object,
        screenshots: list[Path],
    ) -> dict:
        if not self._api_key:
            raise ValueError("API key mode requires a Gemini or Vertex API key.")

        parts: list[dict[str, object]] = [
            {"text": prompt},
            {"text": json.dumps(payload, indent=2)},
        ]
        for path in screenshots:
            import base64

            parts.append(
                {
                    "inline_data": {
                        "mime_type": self._detect_mime_type(path),
                        "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                    }
                }
            )

        response = requests.post(
            f"https://aiplatform.googleapis.com/v1beta1/publishers/google/models/{self.config.llm_model}:generateContent",
            params={"key": self._api_key},
            json={
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                },
            },
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
        text = (
            body.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text")
        )
        if not text:
            raise ValueError("Gemini API key request returned no text content.")
        cleaned = self._strip_code_fence(text)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError("Gemini API key response returned malformed JSON.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Gemini API key response must be a JSON object.")
        return parsed

    def _dedupe_preserve_order(self, entries: list[dict[str, object]]) -> list[dict[str, object]]:
        seen: set[str] = set()
        deduped: list[dict[str, object]] = []
        for entry in entries:
            marker = json.dumps(entry, sort_keys=True, default=str)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(entry)
        return deduped

    def _detect_mime_type(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".png":
            return "image/png"
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        return "application/octet-stream"

    def _extract_json(self, response: object) -> dict:
        text = getattr(response, "text", None)
        if not text:
            raise ValueError("Vertex Gemini returned no text content.")
        cleaned = self._strip_code_fence(text)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError("Vertex Gemini returned malformed JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Vertex Gemini response must be a JSON object.")
        return payload

    def _strip_code_fence(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3:
                return "\n".join(lines[1:-1]).strip()
        return stripped
