# Privacy-First Backend Setup

## 1) Configure environment

Copy `.env.example` to `.env` and set:

- `INSFORGE_BASE_URL`
- `INSFORGE_PROJECT_ID`
- `INSFORGE_API_KEY`
- `INSFORGE_AUTH_ENABLED=true`
- `INSFORGE_AUTH_TOKEN` (copied from existing authenticated frontend)
- `INSFORGE_CURRENT_USER_ID` (optional if token introspection is available)
- `DEFAULT_WORKFLOW_VISIBILITY=private`
- `ENABLE_TEAM_SHARING=true`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `GOOGLE_APPLICATION_CREDENTIALS`

## 2) Create schema

Run SQL from `insforge_schema.sql` in your InsForge project.
Then run `auth_migration.sql` to add ownership columns and RLS policies.

Remote tables:

- `sessions`
- `chunk_summaries`
- `final_pseudocode`
- `workflow_templates`
- `workflow_insights`
- `workflow_search_index`
- `agent_handoff_queue`

## 3) Privacy contract

InsForge receives only:

- session metadata
- chunk summaries
- final pseudocode
- optional suggestions
- workflow templates
- workflow search index records
- workflow insights
- agent handoff drafts

InsForge never receives:

- screenshots
- OCR text
- mouse coordinates
- keyboard events
- raw local event logs

Chunk summaries and final pseudocode remain in local SQLite and are also sent to InsForge when cloud sync is enabled.
All safe synced records include `user_id` and respect private/team visibility.

## 4) Run tracker

Local-only:

```bash
tracker start --llm-provider mock
```

Cloud summary sync:

```bash
tracker start --cloud-sync --llm-provider vertex_gemini
tracker start --cloud-sync --visibility team --llm-provider vertex_gemini
```

Auth utilities:

```bash
tracker auth login
tracker auth status
tracker auth logout
```
