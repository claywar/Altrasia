import { useState } from "react";
import { api, type Scene } from "../api/client";
import { SettingsBlock } from "./settings/SettingsBlock";

type Props = {
  worldId: string;
  scenes: Scene[];
  activeSceneId: string;
  embedded?: boolean;
};

export function BriefingPanel({ worldId, scenes, activeSceneId, embedded }: Props) {
  const [sceneId, setSceneId] = useState(activeSceneId);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const form = (
    <div className="settings-fields">
      <label className="settings-field">
        <span className="settings-field-label">Scene</span>
        <select value={sceneId} onChange={(e) => setSceneId(e.target.value)}>
          {scenes.map((s) => (
            <option key={s.sceneId} value={s.sceneId}>
              {s.locationName}
            </option>
          ))}
        </select>
      </label>
      <label className="settings-field">
        <span className="settings-field-label">Briefing text</span>
        <textarea
          className="char-draft-brief"
          rows={3}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Facts visible on the briefing board at this location…"
        />
      </label>
      <button
        type="button"
        disabled={busy || !text.trim()}
        onClick={async () => {
          setBusy(true);
          setMsg(null);
          try {
            const out = await api.setBriefing(worldId, sceneId, { text: text.trim() });
            setMsg(`Posted to ${out.locusKey}`);
            setText("");
          } catch (e) {
            setMsg(e instanceof Error ? e.message : "Failed");
          } finally {
            setBusy(false);
          }
        }}
      >
        Post briefing
      </button>
      {msg && <p className="settings-block-foot">{msg}</p>}
    </div>
  );

  if (embedded) {
    return (
      <SettingsBlock
        title="Briefing board"
        description="Post shared facts at a scene (fixture + world pool mirror)."
      >
        {form}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section">
      <h3>Briefing board</h3>
      <p className="settings-muted">Post shared facts at a scene (fixture + world pool mirror).</p>
      {form}
    </section>
  );
}
