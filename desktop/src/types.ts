export type RecorderStatus =
  | "idle"
  | "recording"
  | "paused"
  | "summarizing"
  | "syncing"
  | "complete"
  | "error";

export type ChunkSummary = {
  chunkIndex: number;
  startedAt: string;
  endedAt: string;
  summary: string;
  observedApps: string[];
  confidence: "high" | "medium" | "low";
  syncStatus: "pending" | "syncing" | "synced" | "failed";
};

export type FinalWorkflow = {
  pseudocode: string[];
  plainText: string;
  automationScore?: number;
  recommendedNextAction?: string;
  templateTitle?: string;
  templateVisibility?: "private" | "team";
  templateOwnerId?: string;
  agentHandoffStatus?: string;
};

export type AppSettings = {
  screenshotIntervalSeconds: number;
  chunkIntervalSeconds: number;
  rawDataTtlSeconds: number;
  llmProvider: string;
  llmModel: string;
  googleCloudProject: string;
  googleCloudLocation: string;
  insforgeBaseUrl: string;
  insforgeProjectId: string;
  insforgeApiKey: string;
  insforgeAuthEnabled: boolean;
  insforgeAuthToken: string;
  insforgeCurrentUserId: string;
  defaultWorkflowVisibility: "private" | "team";
  enableTeamSharing: boolean;
  cloudSyncEnabled: boolean;
  hasInsforgeApiKey: boolean;
  hasInsforgeAuthToken: boolean;
};

export type RecorderEvent =
  | {
    type: "session_started";
    session_id: string;
    started_at: string;
  }
  | {
    type: "capture_tick";
    screenshot_count: number;
    event_count: number;
  }
  | {
    type: "chunk_started";
    session_id: string;
    chunk_index: number;
    started_at: string;
    ended_at: string;
  }
  | {
    type: "gemini_started";
    chunk_index: number;
  }
  | {
    type: "chunk_summary_created";
    chunk_index: number;
    started_at: string;
    ended_at: string;
    summary: string;
    observed_apps: string[];
    confidence: "high" | "medium" | "low";
  }
  | {
    type: "insforge_sync_started" | "insforge_sync_complete";
    record_type: string;
    chunk_index?: number;
    session_id?: string;
  }
  | {
    type: "final_pseudocode_started";
    session_id: string;
  }
  | {
    type: "final_pseudocode_created";
    session_id: string;
    pseudocode: string[];
    plain_text: string;
    automation_score?: number;
    recommended_next_action?: string;
  }
  | {
    type: "workflow_template_created";
    session_id: string;
    title: string;
    category: string;
    tags: string[];
    visibility?: "private" | "team";
    user_id?: string;
  }
  | {
    type: "agent_handoff_created";
    session_id: string;
    status: string;
    proposed_action: string;
  }
  | {
    type: "session_paused" | "session_resumed";
    session_id?: string | null;
  }
  | {
    type: "session_complete";
    session_id: string;
    ended_at: string;
  }
  | {
    type: "error";
    message: string;
    recoverable: boolean;
  };

export type PipelineStep = {
  id: string;
  label: string;
  description: string;
  state: "pending" | "active" | "complete" | "error";
};
