from __future__ import annotations

import requests

from tracker.config import TrackerConfig
from tracker.privacy import assert_remote_payload_allowed


class InsForgeClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        auth_token: str | None = None,
        current_user_id: str | None = None,
        auth_enabled: bool = True,
        summaries_table: str = "chunk_summaries",
        final_table: str = "final_pseudocode",
        workflow_insights_table: str = "workflow_insights",
        workflow_templates_table: str = "workflow_templates",
        agent_handoff_table: str = "agent_handoff_queue",
        workflow_search_table: str = "workflow_search_index",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.auth_token = auth_token
        self.current_user_id = current_user_id
        self.auth_enabled = auth_enabled
        self.summaries_table = summaries_table
        self.final_table = final_table
        self.workflow_insights_table = workflow_insights_table
        self.workflow_templates_table = workflow_templates_table
        self.agent_handoff_table = agent_handoff_table
        self.workflow_search_table = workflow_search_table

    @classmethod
    def from_config(cls, config: TrackerConfig) -> InsForgeClient:
        return cls(
            base_url=str(config.insforge_base_url),
            api_key=str(config.insforge_api_key),
            auth_token=config.insforge_auth_token,
            current_user_id=config.insforge_current_user_id,
            auth_enabled=config.insforge_auth_enabled,
            summaries_table=config.insforge_summaries_table,
            final_table=config.insforge_final_table,
            workflow_insights_table=config.insforge_workflow_insights_table,
            workflow_templates_table=config.insforge_workflow_templates_table,
            agent_handoff_table=config.insforge_agent_handoff_table,
            workflow_search_table=config.insforge_workflow_search_table,
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _require_auth(self) -> None:
        if self.auth_enabled and not self.auth_token:
            raise ValueError("InsForge auth is enabled but no auth token is configured.")

    def _resolve_current_user_id(self) -> str | None:
        if self.current_user_id:
            return self.current_user_id
        if not self.auth_token:
            return None
        user = self.get_current_user()
        user_id = user.get("id")
        if isinstance(user_id, str) and user_id.strip():
            self.current_user_id = user_id
            return self.current_user_id
        return None

    def _prepare_payload(self, table: str, payload: dict) -> dict:
        prepared = dict(payload)
        current_user_id = self._resolve_current_user_id()
        if "user_id" in prepared:
            if current_user_id:
                prepared["user_id"] = current_user_id
            elif self.auth_enabled and not prepared.get("user_id"):
                raise ValueError("InsForge auth is enabled but user_id could not be resolved.")

        if table == "sessions":
            prepared.setdefault("visibility", "private")
        if table == self.workflow_templates_table:
            visibility = str(prepared.get("visibility") or "private")
            prepared["visibility"] = visibility
            prepared["shared_with_team"] = visibility == "team"
        if table == self.workflow_search_table:
            prepared.setdefault("visibility", "private")

        return prepared

    def get_current_user(self) -> dict:
        self._require_auth()
        paths = (
            "/api/auth/user",
            "/api/auth/me",
            "/api/auth/session/user",
        )
        for path in paths:
            response = requests.get(
                f"{self.base_url}{path}",
                headers=self._headers(),
                timeout=10,
            )
            if response.status_code == 404:
                continue
            response.raise_for_status()
            if not response.content:
                return {}
            parsed = response.json()
            if isinstance(parsed, dict):
                if isinstance(parsed.get("user"), dict):
                    return parsed["user"]
                return parsed
        return {}

    def create_session(self, payload: dict) -> dict:
        self._require_auth()
        prepared = self._prepare_payload("sessions", payload)
        assert_remote_payload_allowed("sessions", prepared)
        return self._insert_record("sessions", prepared)

    def upload_chunk_summary(self, payload: dict) -> dict:
        self._require_auth()
        prepared = self._prepare_payload("chunk_summaries", payload)
        assert_remote_payload_allowed("chunk_summaries", prepared)
        return self._insert_record(self.summaries_table, prepared)

    def upload_final_pseudocode(self, payload: dict) -> dict:
        self._require_auth()
        prepared = self._prepare_payload("final_pseudocode", payload)
        assert_remote_payload_allowed("final_pseudocode", prepared)
        return self._insert_record(self.final_table, prepared)

    def upload_workflow_insight(self, payload: dict) -> dict:
        self._require_auth()
        prepared = self._prepare_payload("workflow_insights", payload)
        assert_remote_payload_allowed("workflow_insights", prepared)
        return self._insert_record(self.workflow_insights_table, prepared)

    def upload_workflow_template(self, payload: dict) -> dict:
        self._require_auth()
        prepared = self._prepare_payload(self.workflow_templates_table, payload)
        assert_remote_payload_allowed("workflow_templates", prepared)
        return self._insert_record(self.workflow_templates_table, prepared)

    def upload_agent_handoff_draft(self, payload: dict) -> dict:
        self._require_auth()
        prepared = self._prepare_payload("agent_handoff_queue", payload)
        assert_remote_payload_allowed("agent_handoff_queue", prepared)
        return self._insert_record(self.agent_handoff_table, prepared)

    def upload_search_index_record(self, payload: dict) -> dict:
        self._require_auth()
        prepared = self._prepare_payload(self.workflow_search_table, payload)
        assert_remote_payload_allowed("workflow_search_index", prepared)
        return self._insert_record(self.workflow_search_table, prepared)

    def search_workflows(
        self,
        query: str,
        limit: int = 10,
        scope: str = "mine",
    ) -> list[dict]:
        self._require_auth()
        current_user_id = self._resolve_current_user_id()
        if scope == "mine" and not current_user_id:
            return []
        records = self._list_records(
            self.workflow_search_table,
            {
                "limit": limit,
                "query": query,
                "user_id": current_user_id if scope == "mine" else None,
                "visibility": "team" if scope == "team" else None,
            },
        )
        normalized_query = query.lower()
        scoped = [
            record
            for record in records
            if normalized_query in str(record.get("searchable_text", "")).lower()
            and self._record_visible_in_scope(record, scope, current_user_id)
        ]
        return scoped[:limit]

    def list_workflow_templates(
        self,
        limit: int = 10,
        scope: str = "mine",
    ) -> list[dict]:
        self._require_auth()
        current_user_id = self._resolve_current_user_id()
        if scope == "mine" and not current_user_id:
            return []
        records = self._list_records(
            self.workflow_templates_table,
            {
                "limit": limit,
                "order_by": "created_at",
                "order": "desc",
                "user_id": current_user_id if scope == "mine" else None,
                "visibility": "team" if scope == "team" else None,
            },
        )
        return [
            record
            for record in records
            if self._record_visible_in_scope(record, scope, current_user_id)
        ][:limit]

    def _record_visible_in_scope(
        self,
        record: dict,
        scope: str,
        current_user_id: str | None,
    ) -> bool:
        record_user_id = record.get("user_id")
        record_visibility = str(record.get("visibility") or "private")
        if scope == "team":
            return record_visibility == "team" or (bool(current_user_id) and record_user_id == current_user_id)
        if scope == "mine":
            return bool(current_user_id) and record_user_id == current_user_id
        return True

    def list_workflow_insights(self, session_id: str | None = None, limit: int = 10) -> list[dict]:
        self._require_auth()
        params = {"limit": limit, "order_by": "created_at", "order": "desc"}
        if session_id:
            params["session_id"] = session_id
        return self._list_records(self.workflow_insights_table, params)

    def get_workflow_template(self, workflow_id: str) -> dict:
        self._require_auth()
        return self._get_record(self.workflow_templates_table, workflow_id)

    def get_agent_handoff(self, session_id: str) -> list[dict]:
        self._require_auth()
        return self._list_records(
            self.agent_handoff_table,
            {"session_id": session_id, "limit": 10, "order_by": "created_at", "order": "desc"},
        )

    def list_final_pseudocode(self, session_id: str) -> list[dict]:
        self._require_auth()
        return self._list_records(
            self.final_table,
            {"session_id": session_id, "limit": 10, "order_by": "created_at", "order": "desc"},
        )

    def _insert_record(self, table: str, payload: dict) -> dict:
        response = requests.post(
            f"{self.base_url}/api/database/records/{table}",
            json=payload,
            headers={**self._headers(), "Prefer": "return=representation"},
            timeout=15,
        )
        response.raise_for_status()
        if not response.content:
            return {}
        parsed = response.json()
        if isinstance(parsed, list):
            return parsed[0] if parsed and isinstance(parsed[0], dict) else {}
        return parsed if isinstance(parsed, dict) else {}

    def _list_records(self, table: str, params: dict[str, object] | None = None) -> list[dict]:
        sanitized_params = {
            key: value for key, value in (params or {}).items() if value is not None
        }
        response = requests.get(
            f"{self.base_url}/api/database/records/{table}",
            params=sanitized_params,
            headers=self._headers(),
            timeout=15,
        )
        response.raise_for_status()
        if not response.content:
            return []
        parsed = response.json()
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            items = parsed.get("data")
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []

    def _get_record(self, table: str, record_id: str) -> dict:
        response = requests.get(
            f"{self.base_url}/api/database/records/{table}/{record_id}",
            headers=self._headers(),
            timeout=15,
        )
        response.raise_for_status()
        if not response.content:
            return {}
        parsed = response.json()
        return parsed if isinstance(parsed, dict) else {}
