import type { PipelineStep } from "../types";
import { CardSurface } from "./ui/CardSurface";
import { Pill } from "./ui/Pill";
import { SectionEyebrow, SectionTitle } from "./ui/Typography";

type Props = {
  steps: PipelineStep[];
  metrics: {
    screenshots: number;
    events: number;
    syncLabel: string;
  };
};

export function PipelineProgress({ steps, metrics }: Props) {
  return (
    <section className="organic-surface rounded-[2rem] rounded-tr-[3.5rem] p-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <SectionEyebrow>Live Pipeline</SectionEyebrow>
          <SectionTitle>Capture to workflow intelligence</SectionTitle>
        </div>
        <CardSurface className="rounded-[1.5rem] px-4 py-3 text-right text-xs text-muted-foreground" tone="muted">
          <div>{metrics.screenshots} screenshots</div>
          <div>{metrics.events} local events</div>
          <div className="max-w-[12rem] text-muted-foreground">{metrics.syncLabel}</div>
        </CardSurface>
      </div>
      <div className="space-y-3">
        {steps.map((step, index) => (
          <CardSurface
            key={step.id}
            className="flex gap-4 rounded-[1.6rem] px-4 py-4"
            interactive
          >
            <div className="flex flex-col items-center">
              <div
                className={`mt-1 flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold ${step.state === "complete"
                    ? "bg-primary text-primary-foreground"
                    : step.state === "active"
                      ? "bg-secondary text-secondary-foreground"
                      : step.state === "error"
                        ? "bg-destructive text-white"
                        : "bg-muted text-muted-foreground"
                  }`}
              >
                {index + 1}
              </div>
              {index < steps.length - 1 ? <div className="mt-2 h-full w-px bg-border/80" /> : null}
            </div>
            <div className="min-w-0 pb-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold text-foreground">{step.label}</p>
                <Pill tone="accent" size="xs">{step.state}</Pill>
              </div>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">{step.description}</p>
            </div>
          </CardSurface>
        ))}
      </div>
    </section>
  );
}
