import type { RecorderStatus } from "../types";
import { RecordingControls } from "./RecordingControls";
import { StatusBadge } from "./StatusBadge";
import { CardSurface } from "./ui/CardSurface";
import { Pill } from "./ui/Pill";
import { SectionEyebrow } from "./ui/Typography";

type Props = {
  status: RecorderStatus;
  sessionTimer: string;
  isBusy: boolean;
  sessionId: string | null;
  syncLabel: string;
  authStatusLabel: string;
  metrics: {
    screenshots: number;
    events: number;
  };
  errorMessage: string | null;
  onStart: () => void;
  onStop: () => void;
  onPauseResume: () => void;
  onOpenSettings: () => void;
};

export function Dashboard({
  status,
  sessionTimer,
  isBusy,
  sessionId,
  syncLabel,
  authStatusLabel,
  metrics,
  errorMessage,
  onStart,
  onStop,
  onPauseResume,
  onOpenSettings,
}: Props) {
  return (
    <div className="space-y-6">
      <section className="organic-surface relative overflow-hidden rounded-[2rem] rounded-tl-[4rem] rounded-br-[3rem] p-6 md:p-7">
        <div className="pointer-events-none absolute -left-16 top-10 h-48 w-48 rounded-[60%_40%_30%_70%_/_60%_30%_70%_40%] bg-primary/10 blur-3xl" />
        <div className="pointer-events-none absolute -right-16 bottom-2 h-52 w-52 rounded-[44%_56%_65%_35%_/_50%_55%_45%_50%] bg-secondary/14 blur-3xl" />
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-3">
                <SectionEyebrow>Workflow Tracker</SectionEyebrow>
                <StatusBadge status={status} />
                <Pill tone="outline" uppercase={false}>Cmd+Shift+R toggle</Pill>
              </div>
              <h1 className="mt-4 max-w-2xl text-[2.15rem] font-semibold leading-tight text-foreground md:text-[2.45rem]">
                Record desktop workflows with a simple local-first control panel.
              </h1>
              <p className="mt-3 max-w-2xl text-[15px] leading-7 text-muted-foreground">
                Start and stop the Python recorder, pause when needed, and keep raw screenshots and
                input data on-device.
              </p>
              <p className="mt-2 text-sm font-medium text-foreground">Auth: {authStatusLabel}</p>
            </div>

            <button
              className="btn-organic-outline px-6 text-sm"
              onClick={onOpenSettings}
            >
              Settings
            </button>
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
            <CardSurface className="rounded-[2rem] rounded-tr-[3.75rem] px-6 py-5 shadow-soft" tone="primary">
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.26em] text-primary-foreground/70">Session timer</div>
                  <div className="mt-2 text-3xl font-semibold">{sessionTimer}</div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.26em] text-primary-foreground/70">Session ID</div>
                  <div className="mt-2 break-all text-sm leading-6 text-primary-foreground">{sessionId ?? "Not started"}</div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.26em] text-primary-foreground/70">Sync status</div>
                  <div className="mt-2 text-sm leading-6 text-primary-foreground">{syncLabel}</div>
                </div>
              </div>
            </CardSurface>

            <CardSurface className="organic-surface rounded-[2rem] rounded-bl-[3.5rem] p-5" tone="base">
              <SectionEyebrow className="tracking-[0.26em]">Session controls</SectionEyebrow>
              <div className="mt-4 space-y-4">
                <RecordingControls
                  status={status}
                  isBusy={isBusy}
                  onStart={onStart}
                  onStop={onStop}
                  onPauseResume={onPauseResume}
                />
                <div className="text-xs leading-6 text-muted-foreground">
                  <div>{metrics.screenshots} screenshots captured</div>
                  <div>{metrics.events} local events recorded</div>
                  <div>Shortcut: Cmd+Shift+R</div>
                </div>
              </div>
            </CardSurface>
          </div>
        </div>

        {status === "idle" ? (
          <div className="mt-6 rounded-[2rem] border border-border/70 bg-muted/72 p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <SectionEyebrow className="tracking-[0.24em]">Before you start</SectionEyebrow>
                <div className="mt-2 text-lg font-semibold text-foreground">
                  Save config, grant macOS permissions, then start a session.
                </div>
              </div>
              <div className="grid gap-2 text-sm text-muted-foreground">
                <div>1. Save capture and sync settings.</div>
                <div>2. Allow screen recording and accessibility access.</div>
                <div>3. Start from the button or the global shortcut.</div>
              </div>
            </div>
          </div>
        ) : null}

        <CardSurface className="mt-6 rounded-[2rem] px-5 py-4 text-sm leading-7" tone="accent">
          Raw screenshots, keystrokes, mouse events, and OCR text stay local. InsForge only receives
          summaries, pseudocode, workflow insights, templates, and agent handoff drafts.
        </CardSurface>

        {errorMessage ? (
          <CardSurface className="mt-6 rounded-[2rem] p-5 text-sm" tone="danger">
            <div className="font-semibold">Recorder error</div>
            <div className="mt-2">{errorMessage}</div>
            <div className="mt-2 text-[#7D3A33]">
              Recovery suggestion: stop the session, verify `.env` values, and retry.
            </div>
          </CardSurface>
        ) : null}
      </section>
    </div>
  );
}
