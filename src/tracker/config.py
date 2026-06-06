from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class TrackerConfig:
    db_path: Path = Path("data/local_tracker.db")
    screenshot_dir: Path = Path("data/screenshots")
    export_dir: Path = Path("data/exports")
    screenshot_interval_seconds: int = 2
    chunk_interval_seconds: int = 6
    raw_data_ttl_seconds: int = 300
    ocr_enabled: bool = True
    local_only_mode: bool = True
    enable_cloud_sync: bool = False
    enable_screenshot_upload: bool = False
    upload_raw_events: bool = False
    upload_screenshots: bool = False
    upload_ocr_text: bool = False
    upload_only_summaries: bool = True
    llm_provider: str = "vertex_gemini"
    llm_model: str = "gemini-1.5-pro"
    vertex_api_key: str | None = None
    google_api_key: str | None = None
    gemini_api_key: str | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str = "us-central1"
    google_application_credentials: str | None = None
    insforge_base_url: str | None = None
    insforge_project_id: str | None = None
    insforge_api_key: str | None = None
    insforge_auth_enabled: bool = True
    insforge_auth_token: str | None = None
    insforge_current_user_id: str | None = None
    default_workflow_visibility: str = "private"
    workflow_visibility: str = "private"
    enable_team_sharing: bool = True
    insforge_storage_bucket: str = "session-screenshots"
    insforge_summaries_table: str = "chunk_summaries"
    insforge_final_table: str = "final_pseudocode"
    enable_workflow_template_creation: bool = True
    enable_workflow_insights: bool = True
    enable_agent_handoff_drafts: bool = True
    agent_handoff_automation_score_threshold: int = 75
    insforge_workflow_templates_table: str = "workflow_templates"
    insforge_workflow_insights_table: str = "workflow_insights"
    insforge_agent_handoff_table: str = "agent_handoff_queue"
    insforge_workflow_search_table: str = "workflow_search_index"

    @classmethod
    def from_env(cls) -> TrackerConfig:
        load_dotenv()

        def as_bool(value: str | None, default: bool) -> bool:
            if value is None:
                return default
            return value.strip().lower() in {"1", "true", "yes", "on"}

        return cls(
            db_path=Path(os.getenv("LOCAL_DB_PATH", "data/local_tracker.db")),
            screenshot_interval_seconds=int(os.getenv("SCREENSHOT_INTERVAL_SECONDS", "2")),
            chunk_interval_seconds=int(os.getenv("CHUNK_INTERVAL_SECONDS", "6")),
            raw_data_ttl_seconds=int(os.getenv("RAW_DATA_TTL_SECONDS", "300")),
            enable_cloud_sync=as_bool(os.getenv("ENABLE_CLOUD_SYNC"), False),
            enable_screenshot_upload=as_bool(os.getenv("ENABLE_SCREENSHOT_UPLOAD"), False),
            upload_raw_events=as_bool(os.getenv("UPLOAD_RAW_EVENTS"), False),
            upload_screenshots=as_bool(os.getenv("UPLOAD_SCREENSHOTS"), False),
            upload_ocr_text=as_bool(os.getenv("UPLOAD_OCR_TEXT"), False),
            upload_only_summaries=as_bool(os.getenv("UPLOAD_ONLY_SUMMARIES"), True),
            llm_provider=os.getenv("LLM_PROVIDER", "vertex_gemini"),
            llm_model=os.getenv("LLM_MODEL", "gemini-1.5-pro"),
            vertex_api_key=os.getenv("VERTEX_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            google_cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            google_application_credentials=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            insforge_base_url=os.getenv("INSFORGE_BASE_URL"),
            insforge_project_id=os.getenv("INSFORGE_PROJECT_ID"),
            insforge_api_key=os.getenv("INSFORGE_API_KEY"),
            insforge_auth_enabled=as_bool(os.getenv("INSFORGE_AUTH_ENABLED"), True),
            insforge_auth_token=os.getenv("INSFORGE_AUTH_TOKEN"),
            insforge_current_user_id=os.getenv("INSFORGE_CURRENT_USER_ID"),
            default_workflow_visibility=os.getenv("DEFAULT_WORKFLOW_VISIBILITY", "private"),
            workflow_visibility=os.getenv("DEFAULT_WORKFLOW_VISIBILITY", "private"),
            enable_team_sharing=as_bool(os.getenv("ENABLE_TEAM_SHARING"), True),
            insforge_storage_bucket=os.getenv(
                "INSFORGE_STORAGE_BUCKET",
                "session-screenshots",
            ),
            insforge_summaries_table=os.getenv("INSFORGE_SUMMARIES_TABLE", "chunk_summaries"),
            insforge_final_table=os.getenv("INSFORGE_FINAL_TABLE", "final_pseudocode"),
            enable_workflow_template_creation=as_bool(
                os.getenv("ENABLE_WORKFLOW_TEMPLATE_CREATION"),
                True,
            ),
            enable_workflow_insights=as_bool(os.getenv("ENABLE_WORKFLOW_INSIGHTS"), True),
            enable_agent_handoff_drafts=as_bool(
                os.getenv("ENABLE_AGENT_HANDOFF_DRAFTS"),
                True,
            ),
            agent_handoff_automation_score_threshold=int(
                os.getenv("AGENT_HANDOFF_AUTOMATION_SCORE_THRESHOLD", "75")
            ),
            insforge_workflow_templates_table=os.getenv(
                "INSFORGE_WORKFLOW_TEMPLATES_TABLE",
                "workflow_templates",
            ),
            insforge_workflow_insights_table=os.getenv(
                "INSFORGE_WORKFLOW_INSIGHTS_TABLE",
                "workflow_insights",
            ),
            insforge_agent_handoff_table=os.getenv(
                "INSFORGE_AGENT_HANDOFF_TABLE",
                "agent_handoff_queue",
            ),
            insforge_workflow_search_table=os.getenv(
                "INSFORGE_WORKFLOW_SEARCH_TABLE",
                "workflow_search_index",
            ),
        )

    def has_insforge_credentials(self) -> bool:
        return bool(self.insforge_base_url and self.insforge_api_key and self.insforge_project_id)

    def ensure_directories(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
