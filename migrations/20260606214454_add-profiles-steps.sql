CREATE TABLE IF NOT EXISTS computer_use_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  description TEXT,
  prompt TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS automation_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  template_id UUID REFERENCES computer_use_templates(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profile_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID NOT NULL REFERENCES automation_profiles(id) ON DELETE CASCADE,
  position INTEGER NOT NULL CHECK (position > 0),
  title TEXT NOT NULL,
  instruction TEXT NOT NULL,
  expected_result TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (profile_id, position)
);

CREATE INDEX IF NOT EXISTS idx_automation_profiles_user_id ON automation_profiles(user_id);

CREATE INDEX IF NOT EXISTS idx_automation_profiles_org_id ON automation_profiles(org_id);

CREATE INDEX IF NOT EXISTS idx_automation_profiles_template_id ON automation_profiles(template_id);

CREATE INDEX IF NOT EXISTS idx_profile_steps_profile_id ON profile_steps(profile_id);

INSERT INTO computer_use_templates (slug, name, description, prompt)
VALUES (
  'computer-use-follow-profile-steps',
  'Computer Use: Follow Profile Steps',
  'Reusable base template for running a computer-use automation from an ordered profile step list.',
  'Use the computer-use skill. Follow the exact ordered steps attached to this profile. Execute each step in sequence, observe the page state after every action, and stop if a step cannot be completed safely. Do not invent extra steps. Return a concise completion report with the final state and any blocked step.'
)
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  prompt = EXCLUDED.prompt,
  updated_at = NOW();
