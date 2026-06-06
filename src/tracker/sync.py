from __future__ import annotations

import requests

from tracker.config import TrackerConfig
from tracker.storage.insforge_client import InsForgeClient
from tracker.storage.local_sqlite import LocalSQLiteRepository


class SyncService:
    def __init__(
        self,
        repository: LocalSQLiteRepository,
        client: InsForgeClient,
        config: TrackerConfig,
    ) -> None:
        self.repository = repository
        self.client = client
        self.config = config

    def _team_visibility_enabled(self) -> bool:
        return self.config.workflow_visibility == "team" and self.config.enable_team_sharing

    def _workflow_visibility(self) -> str:
        return "team" if self._team_visibility_enabled() else "private"

    def sync_all(self) -> dict[str, int]:
        synced_sessions = 0
        synced_chunk_summaries = 0
        synced_final_pseudocode = 0
        synced_workflow_insights = 0
        synced_workflow_templates = 0
        synced_agent_handoff_drafts = 0
        synced_workflow_search_index_records = 0

        for session in self.repository.list_unsynced_sessions():
            created = self.client.create_session(
                {
                    "id": session.id,
                    "user_id": session.user_id,
                    "started_at": session.started_at.isoformat(),
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "session_name": session.session_name,
                    "device_name": session.device_name,
                    "os_name": session.os_name,
                    "visibility": "private",
                }
            )
            self.repository.mark_session_synced(session.id, created.get("id"))
            synced_sessions += 1

        for summary in self.repository.list_unsynced_chunk_summaries():
            created_summary = self.client.upload_chunk_summary(
                {
                    "id": summary.id,
                    "session_id": summary.session_id,
                    "user_id": summary.user_id,
                    "chunk_index": summary.chunk_index,
                    "started_at": summary.started_at,
                    "ended_at": summary.ended_at,
                    "summary": summary.summary,
                    "observed_apps": summary.observed_apps,
                    "confidence": summary.confidence,
                }
            )
            self.repository.mark_chunk_summary_synced(summary.id, created_summary.get("id"))
            synced_chunk_summaries += 1

        for final in self.repository.list_unsynced_final_pseudocode():
            try:
                created_final = self.client.upload_final_pseudocode(
                    {
                        "id": final.id,
                        "session_id": final.session_id,
                        "user_id": final.user_id,
                        "pseudocode": final.pseudocode,
                        "plain_text": final.plain_text,
                        "suggestions": final.suggestions,
                    }
                )
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 404:
                    raise
                created_final = {}
            self.repository.mark_final_pseudocode_synced(final.id, created_final.get("id"))
            synced_final_pseudocode += 1

        for insight in self.repository.list_unsynced_workflow_insights():
            try:
                created_insight = self.client.upload_workflow_insight(
                    {
                        "id": insight.id,
                        "session_id": insight.session_id,
                        "user_id": insight.user_id,
                        "summary": insight.summary,
                        "main_apps": insight.main_apps,
                        "detected_task_type": insight.detected_task_type,
                        "tags": insight.tags,
                        "automation_score": insight.automation_score,
                        "automation_reason": insight.automation_reason,
                        "recommended_next_action": insight.recommended_next_action,
                    }
                )
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 404:
                    raise
                created_insight = {}
            self.repository.mark_workflow_insight_synced(insight.id, created_insight.get("id"))
            synced_workflow_insights += 1

        for template in self.repository.list_unsynced_workflow_templates():
            try:
                created_template = self.client.upload_workflow_template(
                    {
                        "id": template.id,
                        "user_id": template.user_id,
                        "session_id": template.session_id,
                        "title": template.title,
                        "description": template.description,
                        "category": template.category,
                        "tags": template.tags,
                        "pseudocode": template.pseudocode,
                        "plain_text": template.plain_text,
                        "visibility": self._workflow_visibility(),
                        "shared_with_team": self._workflow_visibility() == "team",
                        "created_from": template.created_from,
                    }
                )
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 404:
                    raise
                created_template = {}
            self.repository.mark_workflow_template_synced(template.id, created_template.get("id"))
            synced_workflow_templates += 1

        for record in self.repository.list_unsynced_workflow_search_index_records():
            try:
                created_record = self.client.upload_search_index_record(
                    {
                        "id": record.id,
                        "user_id": record.user_id,
                        "session_id": record.session_id,
                        "template_id": record.template_id,
                        "searchable_text": record.searchable_text,
                        "tags": record.tags,
                        "visibility": self._workflow_visibility(),
                    }
                )
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 404:
                    raise
                created_record = {}
            self.repository.mark_workflow_search_index_record_synced(
                record.id,
                created_record.get("id"),
            )
            synced_workflow_search_index_records += 1

        for draft in self.repository.list_unsynced_agent_handoff_drafts():
            created_draft = self.client.upload_agent_handoff_draft(
                {
                    "id": draft.id,
                    "session_id": draft.session_id,
                    "user_id": draft.user_id,
                    "template_id": draft.template_id,
                    "status": draft.status,
                    "proposed_action": draft.proposed_action,
                    "action_plan": draft.action_plan,
                    "requires_user_approval": draft.requires_user_approval,
                    "approved_at": draft.approved_at.isoformat() if draft.approved_at else None,
                    "executed_at": draft.executed_at.isoformat() if draft.executed_at else None,
                }
            )
            self.repository.mark_agent_handoff_draft_synced(draft.id, created_draft.get("id"))
            synced_agent_handoff_drafts += 1

        return {
            "sessions": synced_sessions,
            "chunk_summaries": synced_chunk_summaries,
            "final_pseudocode": synced_final_pseudocode,
            "workflow_insights": synced_workflow_insights,
            "workflow_templates": synced_workflow_templates,
            "workflow_search_index": synced_workflow_search_index_records,
            "agent_handoff_queue": synced_agent_handoff_drafts,
        }

    def sync_session(self, session_id: str) -> dict[str, int]:
        synced_chunk_summaries = 0
        synced_final_pseudocode = 0
        synced_workflow_insights = 0
        synced_workflow_templates = 0
        synced_agent_handoff_drafts = 0
        synced_workflow_search_index_records = 0

        session = self.repository.get_session(session_id)
        if session and not session.synced:
            created = self.client.create_session(
                {
                    "id": session.id,
                    "user_id": session.user_id,
                    "started_at": session.started_at.isoformat(),
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "session_name": session.session_name,
                    "device_name": session.device_name,
                    "os_name": session.os_name,
                    "visibility": "private",
                }
            )
            self.repository.mark_session_synced(session.id, created.get("id"))

        for summary in self.repository.list_unsynced_chunk_summaries(session_id):
            created_summary = self.client.upload_chunk_summary(
                {
                    "id": summary.id,
                    "session_id": summary.session_id,
                    "user_id": summary.user_id,
                    "chunk_index": summary.chunk_index,
                    "started_at": summary.started_at,
                    "ended_at": summary.ended_at,
                    "summary": summary.summary,
                    "observed_apps": summary.observed_apps,
                    "confidence": summary.confidence,
                }
            )
            self.repository.mark_chunk_summary_synced(summary.id, created_summary.get("id"))
            synced_chunk_summaries += 1

        for final in self.repository.list_unsynced_final_pseudocode(session_id):
            try:
                created_final = self.client.upload_final_pseudocode(
                    {
                        "id": final.id,
                        "session_id": final.session_id,
                        "user_id": final.user_id,
                        "pseudocode": final.pseudocode,
                        "plain_text": final.plain_text,
                        "suggestions": final.suggestions,
                    }
                )
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 404:
                    raise
                created_final = {}
            self.repository.mark_final_pseudocode_synced(final.id, created_final.get("id"))
            synced_final_pseudocode += 1

        for insight in self.repository.list_unsynced_workflow_insights(session_id):
            try:
                created_insight = self.client.upload_workflow_insight(
                    {
                        "id": insight.id,
                        "session_id": insight.session_id,
                        "user_id": insight.user_id,
                        "summary": insight.summary,
                        "main_apps": insight.main_apps,
                        "detected_task_type": insight.detected_task_type,
                        "tags": insight.tags,
                        "automation_score": insight.automation_score,
                        "automation_reason": insight.automation_reason,
                        "recommended_next_action": insight.recommended_next_action,
                    }
                )
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 404:
                    raise
                created_insight = {}
            self.repository.mark_workflow_insight_synced(insight.id, created_insight.get("id"))
            synced_workflow_insights += 1

        for template in self.repository.list_unsynced_workflow_templates(session_id):
            try:
                created_template = self.client.upload_workflow_template(
                    {
                        "id": template.id,
                        "user_id": template.user_id,
                        "session_id": template.session_id,
                        "title": template.title,
                        "description": template.description,
                        "category": template.category,
                        "tags": template.tags,
                        "pseudocode": template.pseudocode,
                        "plain_text": template.plain_text,
                        "visibility": self._workflow_visibility(),
                        "shared_with_team": self._workflow_visibility() == "team",
                        "created_from": template.created_from,
                    }
                )
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 404:
                    raise
                created_template = {}
            self.repository.mark_workflow_template_synced(template.id, created_template.get("id"))
            synced_workflow_templates += 1

        for record in self.repository.list_unsynced_workflow_search_index_records(session_id):
            try:
                created_record = self.client.upload_search_index_record(
                    {
                        "id": record.id,
                        "user_id": record.user_id,
                        "session_id": record.session_id,
                        "template_id": record.template_id,
                        "searchable_text": record.searchable_text,
                        "tags": record.tags,
                        "visibility": self._workflow_visibility(),
                    }
                )
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 404:
                    raise
                created_record = {}
            self.repository.mark_workflow_search_index_record_synced(
                record.id,
                created_record.get("id"),
            )
            synced_workflow_search_index_records += 1

        for draft in self.repository.list_unsynced_agent_handoff_drafts(session_id):
            created_draft = self.client.upload_agent_handoff_draft(
                {
                    "id": draft.id,
                    "session_id": draft.session_id,
                    "user_id": draft.user_id,
                    "template_id": draft.template_id,
                    "status": draft.status,
                    "proposed_action": draft.proposed_action,
                    "action_plan": draft.action_plan,
                    "requires_user_approval": draft.requires_user_approval,
                    "approved_at": draft.approved_at.isoformat() if draft.approved_at else None,
                    "executed_at": draft.executed_at.isoformat() if draft.executed_at else None,
                }
            )
            self.repository.mark_agent_handoff_draft_synced(draft.id, created_draft.get("id"))
            synced_agent_handoff_drafts += 1

        return {
            "chunk_summaries": synced_chunk_summaries,
            "final_pseudocode": synced_final_pseudocode,
            "workflow_insights": synced_workflow_insights,
            "workflow_templates": synced_workflow_templates,
            "workflow_search_index": synced_workflow_search_index_records,
            "agent_handoff_queue": synced_agent_handoff_drafts,
        }
