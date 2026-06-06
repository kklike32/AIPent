from tracker.events import ChunkSummary, FinalPseudocode
from tracker.workflows import (
    AgentHandoffPlanner,
    AutomationScorer,
    WorkflowInsightGenerator,
    WorkflowSearchIndexBuilder,
    WorkflowTemplateGenerator,
    build_workflow_artifacts,
)


def _sample_summaries() -> list[ChunkSummary]:
    return [
        ChunkSummary(
            session_id="session-1",
            chunk_index=0,
            started_at="2026-01-01T00:00:00+00:00",
            ended_at="2026-01-01T00:00:06+00:00",
            summary="Opened a spreadsheet, selected a table, and prepared a chart.",
            observed_apps=["Excel", "Chrome"],
            confidence="high",
        ),
        ChunkSummary(
            session_id="session-1",
            chunk_index=1,
            started_at="2026-01-01T00:00:06+00:00",
            ended_at="2026-01-01T00:00:12+00:00",
            summary="Formatted the chart, renamed it, and exported a report.",
            observed_apps=["Excel"],
            confidence="high",
        ),
    ]


def _sample_final() -> FinalPseudocode:
    return FinalPseudocode(
        session_id="session-1",
        pseudocode=[
            "Step 1. Open the spreadsheet and select the reporting table.",
            "Step 2. Create a chart from the selected data.",
            "Step 3. Format the chart, rename it, and export the report.",
        ],
        plain_text=(
            "1. Open the spreadsheet and select the reporting table.\n"
            "2. Create a chart from the selected data.\n"
            "3. Format the chart, rename it, and export the report."
        ),
        suggestions=["Create a reusable workflow template and draft a Python automation plan."],
    )


def test_automation_scoring_prefers_repeatable_structured_workflows() -> None:
    score, reason = AutomationScorer().score(
        _sample_final().pseudocode,
        [summary.summary for summary in _sample_summaries()],
    )

    assert score >= 75
    assert "structured" in reason.lower()


def test_workflow_insight_generation() -> None:
    insight = WorkflowInsightGenerator().generate(_sample_final(), _sample_summaries())

    assert insight.detected_task_type == "spreadsheet_automation"
    assert insight.main_apps[0] == "Excel"
    assert "automation_candidate" in insight.tags
    assert insight.automation_score >= 75


def test_workflow_template_generation() -> None:
    insight = WorkflowInsightGenerator().generate(_sample_final(), _sample_summaries())
    template = WorkflowTemplateGenerator().generate(_sample_final(), insight)

    assert "spreadsheet" in template.category
    assert "chart" in template.title.lower()
    assert template.pseudocode == _sample_final().pseudocode


def test_agent_handoff_draft_generation() -> None:
    insight = WorkflowInsightGenerator().generate(_sample_final(), _sample_summaries())
    template = WorkflowTemplateGenerator().generate(_sample_final(), insight)
    draft = AgentHandoffPlanner().create_draft(template, _sample_final(), insight.automation_score)

    assert draft.status == "draft"
    assert draft.requires_user_approval is True
    assert len(draft.action_plan) >= 3


def test_search_index_excludes_raw_ocr_and_events() -> None:
    insight = WorkflowInsightGenerator().generate(_sample_final(), _sample_summaries())
    template = WorkflowTemplateGenerator().generate(_sample_final(), insight)
    record = WorkflowSearchIndexBuilder().build(_sample_final(), insight, template)

    assert "ocr" not in record.searchable_text.lower()
    assert "mouse_click" not in record.searchable_text.lower()
    assert "raw event" not in record.searchable_text.lower()


def test_high_automation_score_creates_handoff_draft() -> None:
    artifacts = build_workflow_artifacts(
        _sample_final(),
        _sample_summaries(),
        handoff_threshold=75,
    )

    assert artifacts.handoff_draft is not None


def test_low_automation_score_does_not_create_handoff_draft() -> None:
    final = FinalPseudocode(
        session_id="session-2",
        pseudocode=[
            "Step 1. Brainstorm a creative concept.",
            "Step 2. Write a judgment-based draft with sensitive private context.",
        ],
        plain_text=(
            "1. Brainstorm a creative concept.\n"
            "2. Write a judgment-based draft with sensitive private context."
        ),
        suggestions=["Have a human review the draft."],
    )
    summaries = [
        ChunkSummary(
            session_id="session-2",
            chunk_index=0,
            started_at="2026-01-01T00:00:00+00:00",
            ended_at="2026-01-01T00:00:06+00:00",
            summary="Brainstormed and drafted creative material with private details.",
            observed_apps=["Docs"],
            confidence="medium",
        )
    ]

    artifacts = build_workflow_artifacts(final, summaries, handoff_threshold=75)

    assert artifacts.insight.automation_score < 75
    assert artifacts.handoff_draft is None


def test_workflow_template_defaults_to_private_visibility() -> None:
    insight = WorkflowInsightGenerator().generate(_sample_final(), _sample_summaries())
    template = WorkflowTemplateGenerator().generate(_sample_final(), insight)

    assert template.visibility == "private"
    assert template.shared_with_team is False


def test_workflow_template_team_visibility_is_opt_in() -> None:
    insight = WorkflowInsightGenerator().generate(_sample_final(), _sample_summaries())
    template = WorkflowTemplateGenerator().generate(_sample_final(), insight)
    template.visibility = "team"
    template.shared_with_team = template.visibility == "team"

    assert template.visibility == "team"
    assert template.shared_with_team is True
