import { useEffect, useMemo, useRef, useState } from "react";
import { register, unregister } from "@tauri-apps/plugin-global-shortcut";
import { Dashboard } from "./components/Dashboard";
import { ChunkSummaryList } from "./components/ChunkSummaryList";
import { FinalWorkflowPanel } from "./components/FinalWorkflowPanel";
import { PipelineProgress } from "./components/PipelineProgress";
import { SettingsPanel } from "./components/SettingsPanel";
import { loadSettings, saveSettings } from "./lib/config";
import {
  listenToRecorderEvents,
  pauseRecorder,
  resumeRecorder,
  showDashboard,
  startRecorder,
  stopRecorder,
} from "./lib/recorderProcess";
import type { AppSettings, ChunkSummary, FinalWorkflow, PipelineStep, RecorderEvent, RecorderStatus } from "./types";

const DEFAULT_SETTINGS: AppSettings = {
  screenshotIntervalSeconds: 2,
  chunkIntervalSeconds: 6,
  rawDataTtlSeconds: 300,
  llmProvider: "vertex_gemini",
  llmModel: "gemini-1.5-pro",
  googleCloudProject: "",
  googleCloudLocation: "us-central1",
  insforgeBaseUrl: "",
  insforgeProjectId: "",
  insforgeApiKey: "",
  insforgeAuthEnabled: true,
  insforgeAuthToken: "",
  insforgeCurrentUserId: "",
  defaultWorkflowVisibility: "private",
  enableTeamSharing: true,
  cloudSyncEnabled: false,
  hasInsforgeApiKey: false,
  hasInsforgeAuthToken: false,
};

const EMPTY_WORKFLOW: FinalWorkflow = {
  pseudocode: [],
  plainText: "",
};

const INITIAL_PIPELINE: PipelineStep[] = [
  {
    id: "capture",
    label: "Screenshot capture every 2s",
    description: "Local recorder captures screenshots and event metadata without uploading raw artifacts.",
    state: "pending",
  },
  {
    id: "chunk",
    label: "6-second chunk builder",
    description: "Buffered local activity is grouped into privacy-safe chunks for summarization.",
    state: "pending",
  },
  {
    id: "gemini",
    label: "Gemini summary generation",
    description: "Each chunk is summarized into observed apps, confidence, and a concise workflow note.",
    state: "pending",
  },
  {
    id: "sync",
    label: "InsForge summary sync",
    description: "Only summaries, pseudocode, insights, templates, and handoff drafts are synced.",
    state: "pending",
  },
  {
    id: "final",
    label: "Final pseudocode generation",
    description: "The session is distilled into reusable pseudocode, automation score, and next action.",
    state: "pending",
  },
];

function formatDuration(ms: number) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

function updateStep(steps: PipelineStep[], id: string, state: PipelineStep["state"]) {
  return steps.map((step) => (step.id === id ? { ...step, state } : step));
}

export default function App() {
  const [tab, setTab] = useState<"dashboard" | "settings">("dashboard");
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [isBusy, setIsBusy] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [sessionActive, setSessionActive] = useState(false);
  const [metrics, setMetrics] = useState({ screenshots: 0, events: 0 });
  const [syncLabel, setSyncLabel] = useState("Waiting for recorder");
  const [chunks, setChunks] = useState<ChunkSummary[]>([]);
  const [workflow, setWorkflow] = useState<FinalWorkflow>(EMPTY_WORKFLOW);
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>(INITIAL_PIPELINE);
  const startedAtRef = useRef<string | null>(null);
  const sessionActiveRef = useRef(false);
  const settingsRef = useRef<AppSettings>(DEFAULT_SETTINGS);
  const statusRef = useRef<RecorderStatus>("idle");

  useEffect(() => {
    startedAtRef.current = startedAt;
  }, [startedAt]);

  useEffect(() => {
    sessionActiveRef.current = sessionActive;
  }, [sessionActive]);

  useEffect(() => {
    settingsRef.current = settings;
  }, [settings]);

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    loadSettings().then(setSettings).catch((error: unknown) => {
      setErrorMessage(String(error));
    });

    let unlisten: (() => void) | undefined;
    listenToRecorderEvents(handleRecorderEvent)
      .then((cleanup) => {
        unlisten = cleanup;
      })
      .catch((error: unknown) => {
        setErrorMessage(String(error));
      });

    register("CommandOrControl+Shift+R", () => {
      void toggleRecording();
    }).catch((error: unknown) => {
      setErrorMessage(String(error));
    });

    return () => {
      if (unlisten) {
        unlisten();
      }
      void unregister("CommandOrControl+Shift+R");
    };
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (!startedAtRef.current || !sessionActiveRef.current) {
        return;
      }
      setElapsedMs(Date.now() - new Date(startedAtRef.current).getTime());
    }, 1000);

    return () => window.clearInterval(timer);
  }, []);

  const sessionTimer = useMemo(() => formatDuration(elapsedMs), [elapsedMs]);
  const authStatusLabel = useMemo(() => {
    if (!settings.insforgeAuthEnabled) {
      return "Not connected";
    }
    if (!settings.hasInsforgeAuthToken && !settings.insforgeAuthToken) {
      return "Not connected";
    }
    if (settings.insforgeCurrentUserId) {
      return `Connected as ${settings.insforgeCurrentUserId}`;
    }
    return "Connected";
  }, [settings]);

  async function toggleRecording() {
    const currentStatus = statusRef.current;
    if (currentStatus === "idle" || currentStatus === "complete" || currentStatus === "error") {
      await handleStart();
    } else {
      await handleStop();
    }
  }

  function resetSessionView() {
    setErrorMessage(null);
    setSessionId(null);
    setStartedAt(null);
    setElapsedMs(0);
    setSessionActive(false);
    setMetrics({ screenshots: 0, events: 0 });
    setSyncLabel("Waiting for recorder");
    setChunks([]);
    setWorkflow(EMPTY_WORKFLOW);
    setPipelineSteps(INITIAL_PIPELINE);
  }

  async function handleStart() {
    setIsBusy(true);
    resetSessionView();
    try {
      await startRecorder();
      await showDashboard();
      setStatus("recording");
    } catch (error) {
      setStatus("error");
      setErrorMessage(String(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleStop() {
    setIsBusy(true);
    setSessionActive(false);
    try {
      await stopRecorder();
    } catch (error) {
      setStatus("error");
      setErrorMessage(String(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handlePauseResume() {
    setIsBusy(true);
    try {
      if (status === "paused") {
        await resumeRecorder();
      } else {
        await pauseRecorder();
      }
    } catch (error) {
      setStatus("error");
      setErrorMessage(String(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleSaveSettings() {
    setIsSaving(true);
    try {
      const saved = await saveSettings(settings);
      setSettings(saved);
      setTab("dashboard");
    } catch (error) {
      setErrorMessage(String(error));
    } finally {
      setIsSaving(false);
    }
  }

  function handleRecorderEvent(event: RecorderEvent) {
    if (event.type === "session_started") {
      setStatus("recording");
      setSessionId(event.session_id);
      setStartedAt(event.started_at);
      setSessionActive(true);
      setSyncLabel("Recorder session started");
      setPipelineSteps(updateStep(INITIAL_PIPELINE, "capture", "active"));
      return;
    }

    if (event.type === "capture_tick") {
      setStatus((current) => (current === "paused" ? current : "recording"));
      setMetrics({ screenshots: event.screenshot_count, events: event.event_count });
      setPipelineSteps((steps) => updateStep(steps, "capture", "complete"));
      return;
    }

    if (event.type === "chunk_started") {
      setStatus("summarizing");
      setPipelineSteps((steps) => updateStep(updateStep(steps, "chunk", "active"), "capture", "complete"));
      return;
    }

    if (event.type === "gemini_started") {
      setStatus("summarizing");
      setPipelineSteps((steps) => updateStep(updateStep(steps, "chunk", "complete"), "gemini", "active"));
      return;
    }

    if (event.type === "chunk_summary_created") {
      setChunks((current) => {
        const next = current.filter((chunk) => chunk.chunkIndex !== event.chunk_index);
        next.push({
          chunkIndex: event.chunk_index,
          startedAt: event.started_at,
          endedAt: event.ended_at,
          summary: event.summary,
          observedApps: event.observed_apps,
          confidence: event.confidence,
          syncStatus: settingsRef.current.cloudSyncEnabled ? "pending" : "synced",
        });
        next.sort((left, right) => left.chunkIndex - right.chunkIndex);
        return next;
      });
      setStatus(settingsRef.current.cloudSyncEnabled ? "syncing" : "recording");
      setPipelineSteps((steps) => updateStep(steps, "gemini", "complete"));
      return;
    }

    if (event.type === "insforge_sync_started") {
      setStatus("syncing");
      setSyncLabel(`Syncing ${event.record_type.replace(/_/g, " ")}`);
      setPipelineSteps((steps) => updateStep(steps, "sync", "active"));
      if (typeof event.chunk_index === "number") {
        setChunks((current) =>
          current.map((chunk) =>
            chunk.chunkIndex === event.chunk_index ? { ...chunk, syncStatus: "syncing" } : chunk,
          ),
        );
      }
      return;
    }

    if (event.type === "insforge_sync_complete") {
      setStatus("recording");
      setSyncLabel(`Synced ${event.record_type.replace(/_/g, " ")}`);
      setPipelineSteps((steps) => updateStep(steps, "sync", "complete"));
      if (typeof event.chunk_index === "number") {
        setChunks((current) =>
          current.map((chunk) =>
            chunk.chunkIndex === event.chunk_index ? { ...chunk, syncStatus: "synced" } : chunk,
          ),
        );
      }
      return;
    }

    if (event.type === "final_pseudocode_started") {
      setStatus("summarizing");
      setPipelineSteps((steps) => updateStep(steps, "final", "active"));
      return;
    }

    if (event.type === "final_pseudocode_created") {
      setWorkflow({
        pseudocode: event.pseudocode,
        plainText: event.plain_text,
        automationScore: event.automation_score,
        recommendedNextAction: event.recommended_next_action,
      });
      setPipelineSteps((steps) => updateStep(steps, "final", "complete"));
      return;
    }

    if (event.type === "workflow_template_created") {
      setWorkflow((current) => ({
        ...current,
        templateTitle: event.title,
        templateVisibility: event.visibility,
        templateOwnerId: event.user_id,
      }));
      return;
    }

    if (event.type === "agent_handoff_created") {
      setWorkflow((current) => ({
        ...current,
        agentHandoffStatus: `${event.status}: ${event.proposed_action}`,
      }));
      return;
    }

    if (event.type === "session_paused") {
      setStatus("paused");
      setSyncLabel("Recording paused");
      return;
    }

    if (event.type === "session_resumed") {
      setStatus("recording");
      setSyncLabel("Recording resumed");
      return;
    }

    if (event.type === "session_complete") {
      setStatus("complete");
      setSyncLabel("Session complete");
      setSessionActive(false);
      return;
    }

    if (event.type === "error") {
      setStatus("error");
      setErrorMessage(event.message);
      setPipelineSteps((steps) => {
        const active = steps.find((step) => step.state === "active")?.id ?? "sync";
        return updateStep(steps, active, "error");
      });
    }
  }

  return (
    <main className="app-shell">
      <div className="app-shell-blobs">
        <div className="absolute -left-28 top-8 h-64 w-64 rounded-[58%_42%_65%_35%_/_45%_55%_45%_55%] bg-primary/14 blur-3xl" />
        <div className="absolute -right-20 top-24 h-72 w-72 rounded-[40%_60%_32%_68%_/_62%_38%_64%_36%] bg-secondary/20 blur-3xl" />
      </div>
      <div className="app-shell-content">
        <div className="app-shell-tabs">
          <div className="app-shell-tab-rail">
            <button
              className={`rounded-full px-5 py-2 text-sm font-bold transition-all duration-300 ${tab === "dashboard"
                ? "bg-primary text-primary-foreground shadow-soft"
                : "text-muted-foreground hover:text-foreground"
                }`}
              onClick={() => setTab("dashboard")}
            >
              Dashboard
            </button>
            <button
              className={`rounded-full px-5 py-2 text-sm font-bold transition-all duration-300 ${tab === "settings"
                ? "bg-primary text-primary-foreground shadow-soft"
                : "text-muted-foreground hover:text-foreground"
                }`}
              onClick={() => setTab("settings")}
            >
              Settings
            </button>
          </div>
        </div>
        {tab === "dashboard" ? (
          <Dashboard
            status={status}
            sessionTimer={sessionTimer}
            isBusy={isBusy}
            sessionId={sessionId}
            syncLabel={syncLabel}
            authStatusLabel={authStatusLabel}
            metrics={metrics}
            errorMessage={errorMessage}
            onStart={() => void handleStart()}
            onStop={() => void handleStop()}
            onPauseResume={() => void handlePauseResume()}
            onOpenSettings={() => setTab("settings")}
          />
        ) : (
          <SettingsPanel
            settings={settings}
            isSaving={isSaving}
            onChange={setSettings}
            onSave={() => void handleSaveSettings()}
            onClose={() => setTab("dashboard")}
          />
        )}

        {tab === "dashboard" ? (
          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <PipelineProgress
              steps={pipelineSteps}
              metrics={{
                screenshots: metrics.screenshots,
                events: metrics.events,
                syncLabel,
              }}
            />
            <div className="grid gap-6">
              <ChunkSummaryList chunks={chunks} />
              <FinalWorkflowPanel workflow={workflow} />
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}
