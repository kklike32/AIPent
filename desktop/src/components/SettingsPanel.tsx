import type { AppSettings } from "../types";
import { SectionEyebrow } from "./ui/Typography";

type Props = {
  settings: AppSettings;
  isSaving: boolean;
  onChange: (next: AppSettings) => void;
  onSave: () => void;
  onClose: () => void;
};

function update<K extends keyof AppSettings>(
  settings: AppSettings,
  key: K,
  value: AppSettings[K],
): AppSettings {
  return { ...settings, [key]: value };
}

export function SettingsPanel({ settings, isSaving, onChange, onSave, onClose }: Props) {
  return (
    <section className="organic-surface rounded-[2rem] rounded-tl-[4rem] p-6">
      <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <SectionEyebrow>Settings</SectionEyebrow>
          <h2 className="mt-2 text-[30px] font-semibold text-foreground">
            Recorder and sync configuration
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground">
            Save demo-safe capture settings locally, then write the approved values back to `.env`
            only when you commit to them.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            className="btn-organic-outline px-6 text-sm"
            onClick={onClose}
          >
            Back
          </button>
          <button
            className="btn-organic-primary px-6 text-sm"
            disabled={isSaving}
            onClick={onSave}
          >
            {isSaving ? "Saving..." : "Save settings"}
          </button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-[1.7rem] border border-border/70 bg-muted/65 p-5">
          <h3 className="text-lg font-semibold text-foreground">Capture</h3>
          <div className="mt-4 grid gap-4">
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Screenshot interval seconds</span>
              <input
                className="organic-input"
                type="number"
                min={1}
                value={settings.screenshotIntervalSeconds}
                onChange={(event) =>
                  onChange(update(settings, "screenshotIntervalSeconds", Number(event.target.value)))
                }
              />
            </label>
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Chunk interval seconds</span>
              <input
                className="organic-input"
                type="number"
                min={1}
                value={settings.chunkIntervalSeconds}
                onChange={(event) =>
                  onChange(update(settings, "chunkIntervalSeconds", Number(event.target.value)))
                }
              />
            </label>
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Raw data TTL seconds</span>
              <input
                className="organic-input"
                type="number"
                min={60}
                value={settings.rawDataTtlSeconds}
                onChange={(event) =>
                  onChange(update(settings, "rawDataTtlSeconds", Number(event.target.value)))
                }
              />
            </label>
          </div>
        </div>

        <div className="rounded-[1.7rem] border border-border/70 bg-muted/65 p-5">
          <h3 className="text-lg font-semibold text-foreground">LLM</h3>
          <div className="mt-4 grid gap-4">
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Provider</span>
              <input
                className="organic-input"
                value={settings.llmProvider}
                onChange={(event) => onChange(update(settings, "llmProvider", event.target.value))}
              />
            </label>
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Model</span>
              <input
                className="organic-input"
                value={settings.llmModel}
                onChange={(event) => onChange(update(settings, "llmModel", event.target.value))}
              />
            </label>
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Google Cloud project</span>
              <input
                className="organic-input"
                value={settings.googleCloudProject}
                onChange={(event) =>
                  onChange(update(settings, "googleCloudProject", event.target.value))
                }
              />
            </label>
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Google Cloud location</span>
              <input
                className="organic-input"
                value={settings.googleCloudLocation}
                onChange={(event) =>
                  onChange(update(settings, "googleCloudLocation", event.target.value))
                }
              />
            </label>
          </div>
        </div>

        <div className="rounded-[1.7rem] border border-border/70 bg-muted/65 p-5">
          <h3 className="text-lg font-semibold text-foreground">InsForge</h3>
          <div className="mt-4 grid gap-4">
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Base URL</span>
              <input
                className="organic-input"
                value={settings.insforgeBaseUrl}
                onChange={(event) => onChange(update(settings, "insforgeBaseUrl", event.target.value))}
              />
            </label>
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Project ID</span>
              <input
                className="organic-input"
                value={settings.insforgeProjectId}
                onChange={(event) =>
                  onChange(update(settings, "insforgeProjectId", event.target.value))
                }
              />
            </label>
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">API key</span>
              <input
                className="organic-input"
                type="password"
                placeholder={
                  settings.hasInsforgeApiKey ? "Saved key is masked. Enter a new key to replace it." : ""
                }
                value={settings.insforgeApiKey}
                onChange={(event) => onChange(update(settings, "insforgeApiKey", event.target.value))}
              />
            </label>
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Auth token (from existing InsForge frontend login)</span>
              <input
                className="organic-input"
                type="password"
                placeholder={
                  settings.hasInsforgeAuthToken
                    ? "Saved token is masked. Enter a new token to replace it."
                    : "Paste short-lived session token"
                }
                value={settings.insforgeAuthToken}
                onChange={(event) => onChange(update(settings, "insforgeAuthToken", event.target.value))}
              />
            </label>
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Current user ID</span>
              <input
                className="organic-input"
                value={settings.insforgeCurrentUserId}
                onChange={(event) =>
                  onChange(update(settings, "insforgeCurrentUserId", event.target.value))
                }
              />
            </label>
            <label className="flex items-center gap-3 rounded-[1.2rem] border border-border/70 bg-white/68 px-4 py-3 text-sm font-semibold text-accent-foreground">
              <input
                className="h-4 w-4 rounded border-border"
                type="checkbox"
                checked={settings.insforgeAuthEnabled}
                onChange={(event) =>
                  onChange(update(settings, "insforgeAuthEnabled", event.target.checked))
                }
              />
              Require InsForge auth token
            </label>
            <label className="flex items-center gap-3 rounded-[1.2rem] border border-border/70 bg-white/68 px-4 py-3 text-sm font-semibold text-accent-foreground">
              <input
                className="h-4 w-4 rounded border-border"
                type="checkbox"
                checked={settings.cloudSyncEnabled}
                onChange={(event) =>
                  onChange(update(settings, "cloudSyncEnabled", event.target.checked))
                }
              />
              Cloud sync enabled
            </label>
          </div>
        </div>

        <div className="rounded-[1.7rem] border border-border/70 bg-muted/65 p-5">
          <h3 className="text-lg font-semibold text-foreground">Workflow sharing</h3>
          <div className="mt-4 grid gap-4">
            <label className="text-sm text-accent-foreground">
              <span className="mb-1 block font-medium">Visibility</span>
              <select
                className="organic-input"
                value={settings.defaultWorkflowVisibility}
                onChange={(event) =>
                  onChange(update(settings, "defaultWorkflowVisibility", event.target.value as "private" | "team"))
                }
              >
                <option value="private">Private</option>
                <option value="team">Team</option>
              </select>
            </label>
            <label className="flex items-center gap-3 rounded-[1.2rem] border border-border/70 bg-white/68 px-4 py-3 text-sm font-semibold text-accent-foreground">
              <input
                className="h-4 w-4 rounded border-border"
                type="checkbox"
                checked={settings.enableTeamSharing}
                onChange={(event) =>
                  onChange(update(settings, "enableTeamSharing", event.target.checked))
                }
              />
              Enable team sharing
            </label>
            <p className="rounded-[1.2rem] border border-border/70 bg-white/68 px-4 py-3 text-xs leading-6 text-muted-foreground">
              Private workflows are only visible to you. Team workflows publish the safe skill
              template and search index, never raw recordings.
            </p>
          </div>
        </div>

        <div className="rounded-[1.7rem] border border-border/70 bg-muted/65 p-5">
          <h3 className="text-lg font-semibold text-foreground">Privacy</h3>
          <div className="mt-4 grid gap-3 text-sm text-accent-foreground">
            <div className="rounded-[1.2rem] border border-border/70 bg-white/68 px-4 py-3">Upload raw screenshots: disabled by design</div>
            <div className="rounded-[1.2rem] border border-border/70 bg-white/68 px-4 py-3">Upload raw keyboard events: disabled by design</div>
            <div className="rounded-[1.2rem] border border-border/70 bg-white/68 px-4 py-3">Upload raw mouse events: disabled by design</div>
            <div className="rounded-[1.2rem] border border-border/70 bg-white/68 px-4 py-3">Upload OCR text: disabled by design</div>
            <div className="rounded-[1.2rem] border border-border/70 bg-white/68 px-4 py-3">Upload summaries only: enabled</div>
          </div>
        </div>
      </div>
    </section>
  );
}
