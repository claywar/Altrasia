import { useEffect, useState } from "react";
import { api, type ImageProfile } from "../api/client";
import { Button } from "../ui/Button";

type Props = {
  worldId: string;
  characterId: string;
  displayName: string;
  defaultPrompt?: string;
  onGenerated?: (result: { assetId?: string; portraitUrl?: string | null }) => void;
};

export function RegenerateImageControl({
  worldId,
  characterId,
  displayName,
  defaultPrompt,
  onGenerated,
}: Props) {
  const [profiles, setProfiles] = useState<ImageProfile[]>([]);
  const [profileId, setProfileId] = useState("");
  const [prompt, setPrompt] = useState(
    defaultPrompt ?? `Portrait of ${displayName}, character study, detailed`
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.listImageProfiles().then((r) => {
      setProfiles(r.profiles.filter((p) => p.supportedWorkflows.includes("character_portrait")));
    });
  }, []);

  const regenerate = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const result = await api.generatePortrait(worldId, characterId, {
        prompt,
        modelProfileId: profileId || undefined,
      });
      if (result.mock) {
        setMessage(result.message ?? "ComfyUI not configured — placeholder only");
      } else if (result.ok) {
        setMessage("Portrait generated");
        onGenerated?.(result);
      } else {
        setMessage(result.error ?? "Generation failed");
      }
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="regenerate-image-control" data-testid="regenerate-image-control">
      <h3>Regenerate portrait</h3>
      <p className="settings-muted">Observer-only (UI-IMG-5). Uses GpuResourceQueue kind: image.</p>
      <label className="settings-field">
        <span className="settings-field-label">Prompt</span>
        <textarea value={prompt} rows={3} disabled={busy} onChange={(e) => setPrompt(e.target.value)} />
      </label>
      <label className="settings-field">
        <span className="settings-field-label">Profile (optional)</span>
        <select value={profileId} disabled={busy} onChange={(e) => setProfileId(e.target.value)}>
          <option value="">Settings default</option>
          {profiles.map((p) => (
            <option key={p.profileId} value={p.profileId}>
              {p.displayName}
            </option>
          ))}
        </select>
      </label>
      <Button variant="secondary" size="sm" disabled={busy} onClick={regenerate}>
        {busy ? "Generating…" : "Regenerate portrait"}
      </Button>
      {message && <p className="settings-muted">{message}</p>}
    </div>
  );
}
