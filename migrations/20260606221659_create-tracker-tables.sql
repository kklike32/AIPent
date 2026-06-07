CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY,
  user_id UUID NULL,
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ NULL,
  session_name TEXT NULL,
  device_name TEXT NULL,
  os_name TEXT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunk_summaries (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  chunk_index INTEGER NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ NOT NULL,
  summary TEXT NOT NULL,
  observed_apps JSONB NULL,
  confidence TEXT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS final_pseudocode (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  pseudocode JSONB NOT NULL,
  plain_text TEXT NOT NULL,
  suggestions JSONB NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_templates (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  title TEXT NOT NULL,
  description TEXT NULL,
  category TEXT NULL,
  tags JSONB DEFAULT '[]'::jsonb,
  pseudocode JSONB NOT NULL,
  plain_text TEXT NOT NULL,
  created_from TEXT DEFAULT 'session_summary',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_insights (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  summary TEXT NOT NULL,
  main_apps JSONB DEFAULT '[]'::jsonb,
  detected_task_type TEXT NULL,
  tags JSONB DEFAULT '[]'::jsonb,
  automation_score INTEGER NOT NULL,
  automation_reason TEXT NULL,
  recommended_next_action TEXT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_handoff_queue (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  template_id UUID NULL REFERENCES workflow_templates(id),
  status TEXT DEFAULT 'draft',
  proposed_action TEXT NOT NULL,
  action_plan JSONB NOT NULL,
  requires_user_approval BOOLEAN DEFAULT TRUE,
  approved_at TIMESTAMPTZ NULL,
  executed_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_search_index (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  template_id UUID NULL REFERENCES workflow_templates(id),
  searchable_text TEXT NOT NULL,
  tags JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
