import { useCallback, useEffect, useState } from "react";
import {
  api,
  type ImageProfile,
  type OperatorSettings,
} from "../../api/client";
import { SettingsBlock } from "./SettingsBlock";

type Props = {
  settings: OperatorSettings;
  onUpdated: (next: OperatorSettings) => void;
};

const WORKFLOW_IDS = [
  "character_portrait",
  "scene_establishing",
  "fixture_icon",
  "map_thumbnail",
] as const;

export function ImageGenerationSettingsSection({ settings, onUpdated }: Props) {
  const [draft, setDraft] = useState(settings.image);
  const [profiles, setProfiles] = useState<ImageProfile[]>([]);
  const [health, setHealth] = useState<{ ok?: boolean; reachable?: boolean; message?: string } | null>(
    null
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newProfile, setNewProfile] = useState({
    profileId: "",
    displayName: "",
    family: "sdxl",
    peakMemoryGb: 8,
    checkpoint: "",
    referenceImage: false,
    supportedWorkflows: ["character_portrait"] as string[],
  });

  useEffect(() => {
    setDraft(settings.image);
  }, [settings.image]);

  const refreshProfiles = useCallback(async () => {
    const r = await api.listImageProfiles();
    setProfiles(r.profiles);
  }, []);

  useEffect(() => {
    refreshProfiles().catch(() => setProfiles([]));
    api.imageHealth().then(setHealth).catch(() => setHealth({ ok: false }));
  }, [refreshProfiles]);

  const saveImage = async (patch: Partial<NonNullable<OperatorSettings["image"]>>) => {
    setBusy(true);
    setError(null);
    try {
      const next = await api.patchOperatorSettings({ image: { ...draft, ...patch } });
      onUpdated(next);
      setDraft(next.image);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const addProfile = async () => {
    setBusy(true);
    setError(null);
    try {
      const comfy =
        newProfile.family === "sdxl"
          ? { checkpoint: newProfile.checkpoint }
          : newProfile.family === "flux"
            ? {
                unet: newProfile.checkpoint,
                clip_l: "clip_l.safetensors",
                clip_t5: "t5xxl_fp16.safetensors",
                vae: "ae.safetensors",
              }
            : {
                diffusionModel: newProfile.checkpoint,
                textEncoder: "qwen_3_4b.safetensors",
                vae: "ae.safetensors",
              };
      await api.createImageProfile({
        profileId: newProfile.profileId,
        family: newProfile.family,
        displayName: newProfile.displayName || newProfile.profileId,
        peakMemoryGb: newProfile.peakMemoryGb,
        comfy,
        capabilities: { referenceImage: newProfile.referenceImage },
        supportedWorkflows: newProfile.supportedWorkflows,
      });
      await refreshProfiles();
      setNewProfile((p) => ({ ...p, profileId: "", displayName: "", checkpoint: "" }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add profile");
    } finally {
      setBusy(false);
    }
  };

  const envComfy = settings.envDefaults?.comfyBaseUrl;

  return (
    <>
      <SettingsBlock
        title="ComfyUI connection"
        description="Native ComfyUI HTTP endpoint (default port 8188). Empty falls back to ALTRASIA_COMFY_URL."
      >
        <div className="settings-fields">
          <label className="settings-field">
            <span className="settings-field-label">ComfyUI base URL</span>
            <input
              type="url"
              placeholder={envComfy || "http://127.0.0.1:8188"}
              value={draft?.comfyBaseUrl ?? ""}
              disabled={busy}
              onChange={(e) => setDraft((d) => ({ ...d!, comfyBaseUrl: e.target.value }))}
              onBlur={() => saveImage({ comfyBaseUrl: draft?.comfyBaseUrl ?? "" })}
            />
          </label>
          <label className="settings-field">
            <span className="settings-field-label">AI memory budget (GB)</span>
            <input
              type="number"
              min={16}
              max={128}
              value={draft?.memoryBudgetGb ?? 70}
              disabled={busy}
              onChange={(e) =>
                setDraft((d) => ({ ...d!, memoryBudgetGb: Number(e.target.value) || 70 }))
              }
              onBlur={() => saveImage({ memoryBudgetGb: draft?.memoryBudgetGb ?? 70 })}
            />
          </label>
          <p className="settings-muted">
            ComfyUI health:{" "}
            {health?.ok ? "reachable" : health?.message ?? "not configured or unreachable"}
          </p>
          {error && <p className="settings-error">{error}</p>}
        </div>
      </SettingsBlock>

      <SettingsBlock
        title="Default image profiles"
        description="Per-workflow profile overrides. Character portraits default to SDXL for reference consistency."
      >
        <div className="settings-fields">
          <label className="settings-field">
            <span className="settings-field-label">Default profile</span>
            <select
              value={draft?.defaultProfileId ?? "sdxl-default"}
              disabled={busy}
              onChange={(e) => {
                const v = e.target.value;
                setDraft((d) => ({ ...d!, defaultProfileId: v }));
                saveImage({ defaultProfileId: v });
              }}
            >
              {profiles.map((p) => (
                <option key={p.profileId} value={p.profileId}>
                  {p.displayName} ({p.peakMemoryGb} GB)
                </option>
              ))}
            </select>
          </label>
          {WORKFLOW_IDS.map((wf) => (
            <label key={wf} className="settings-field">
              <span className="settings-field-label">{wf.replace(/_/g, " ")}</span>
              <select
                value={draft?.workflowProfiles?.[wf] ?? ""}
                disabled={busy}
                onChange={(e) => {
                  const wfProfiles = { ...(draft?.workflowProfiles ?? {}) };
                  if (e.target.value) wfProfiles[wf] = e.target.value;
                  else delete wfProfiles[wf];
                  setDraft((d) => ({ ...d!, workflowProfiles: wfProfiles }));
                  saveImage({ workflowProfiles: wfProfiles });
                }}
              >
                <option value="">Use default profile</option>
                {profiles
                  .filter((p) => p.supportedWorkflows.includes(wf))
                  .map((p) => (
                    <option key={p.profileId} value={p.profileId}>
                      {p.displayName}
                    </option>
                  ))}
              </select>
            </label>
          ))}
        </div>
      </SettingsBlock>

      <SettingsBlock title="Add profile" description="Register a custom checkpoint without editing YAML.">
        <div className="settings-fields">
          <label className="settings-field">
            <span className="settings-field-label">Profile id (slug)</span>
            <input
              value={newProfile.profileId}
              disabled={busy}
              onChange={(e) => setNewProfile((p) => ({ ...p, profileId: e.target.value }))}
            />
          </label>
          <label className="settings-field">
            <span className="settings-field-label">Display name</span>
            <input
              value={newProfile.displayName}
              disabled={busy}
              onChange={(e) => setNewProfile((p) => ({ ...p, displayName: e.target.value }))}
            />
          </label>
          <label className="settings-field">
            <span className="settings-field-label">Family</span>
            <select
              value={newProfile.family}
              disabled={busy}
              onChange={(e) => setNewProfile((p) => ({ ...p, family: e.target.value }))}
            >
              <option value="sdxl">SDXL</option>
              <option value="flux">FLUX</option>
              <option value="z_image_turbo">Z-Image Turbo</option>
            </select>
          </label>
          <label className="settings-field">
            <span className="settings-field-label">Primary checkpoint / model file</span>
            <input
              value={newProfile.checkpoint}
              disabled={busy}
              onChange={(e) => setNewProfile((p) => ({ ...p, checkpoint: e.target.value }))}
            />
          </label>
          <label className="settings-field">
            <span className="settings-field-label">Peak memory (GB)</span>
            <input
              type="number"
              value={newProfile.peakMemoryGb}
              disabled={busy}
              onChange={(e) =>
                setNewProfile((p) => ({ ...p, peakMemoryGb: Number(e.target.value) || 8 }))
              }
            />
          </label>
          <label className="settings-list-item-label">
            <input
              type="checkbox"
              checked={newProfile.referenceImage}
              disabled={busy}
              onChange={(e) => setNewProfile((p) => ({ ...p, referenceImage: e.target.checked }))}
            />
            <span className="settings-list-text">Reference image / IP-Adapter support</span>
          </label>
          <button type="button" className="people-primary" disabled={busy || !newProfile.profileId} onClick={addProfile}>
            Add profile
          </button>
        </div>
      </SettingsBlock>
    </>
  );
}
