import type { FinalWorkflow } from "../types";
import { CardSurface } from "./ui/CardSurface";
import { SectionEyebrow, SectionTitle } from "./ui/Typography";

type Props = {
  workflow: FinalWorkflow;
};

export function FinalWorkflowPanel({ workflow }: Props) {
  return (
    <section className="organic-surface rounded-[2rem] rounded-tl-[3.25rem] p-6">
      <div className="mb-6">
        <SectionEyebrow>Final Workflow</SectionEyebrow>
        <SectionTitle>Pseudocode and next action</SectionTitle>
      </div>

      {workflow.pseudocode.length === 0 ? (
        <CardSurface className="rounded-[1.7rem] border-dashed p-6 text-sm text-muted-foreground" tone="muted">
          Final pseudocode will appear after the recorder stops, chunk summaries finish, and workflow insights are generated.
        </CardSurface>
      ) : (
        <>
          <ol className="space-y-3 text-sm leading-6 text-accent-foreground">
            {workflow.pseudocode.map((step, index) => (
              <li
                key={`${index}-${step}`}
                className="flex gap-3 rounded-[1.35rem] border border-border/70 bg-white/62 px-4 py-4 transition-all duration-300 hover:-translate-y-1 hover:shadow-soft"
              >
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                  {index + 1}
                </span>
                <span>{step.replace(/^Step \d+\.\s*/, "")}</span>
              </li>
            ))}
          </ol>

          <div className="mt-5 grid gap-3">
            <CardSurface className="rounded-[1.35rem] px-4 py-4 text-primary-foreground shadow-soft" tone="primary">
              <SectionEyebrow className="tracking-[0.24em] text-primary-foreground/70">Automation score</SectionEyebrow>
              <div className="mt-2 text-3xl font-semibold">{workflow.automationScore ?? "--"}</div>
            </CardSurface>
            <CardSurface className="rounded-[1.35rem] px-4 py-4 text-sm text-accent-foreground" tone="accent">
              <SectionEyebrow className="tracking-[0.24em]">Recommended next action</SectionEyebrow>
              <div className="mt-2 font-medium text-foreground">
                {workflow.recommendedNextAction ?? "Pending workflow insight generation."}
              </div>
            </CardSurface>
            <CardSurface className="rounded-[1.35rem] px-4 py-4 text-sm text-accent-foreground" tone="base">
              <SectionEyebrow className="tracking-[0.24em]">Workflow template</SectionEyebrow>
              <div className="mt-2 font-medium text-foreground">
                {workflow.templateTitle ?? "Not created yet"}
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                Visibility: {workflow.templateVisibility ?? "private"}
              </div>
              {workflow.templateOwnerId ? (
                <div className="mt-1 text-xs text-muted-foreground">
                  Created by: {workflow.templateOwnerId}
                </div>
              ) : null}
            </CardSurface>
            <CardSurface className="rounded-[1.35rem] px-4 py-4 text-sm text-accent-foreground" tone="base">
              <SectionEyebrow className="tracking-[0.24em]">Agent handoff</SectionEyebrow>
              <div className="mt-2 font-medium text-foreground">
                {workflow.agentHandoffStatus ?? "No draft available yet"}
              </div>
            </CardSurface>
          </div>
        </>
      )}
    </section>
  );
}
