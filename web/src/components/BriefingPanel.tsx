import { useState } from "react";
import { api, type Scene } from "../api/client";

type Props = {
  worldId: string;
  scenes: Scene[];
  activeSceneId: string;
};

export function BriefingPanel({ worldId, scenes, activeSceneId }: Props) {
  const [sceneId, setSceneId] = useState(activeSceneId);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  return (
    <section className="settings-section">
      <h3>Briefing board</h3>
      <p className="settings-muted">
        Post shared facts at a scene (fixture + world pool mirror).
      </p>
      <label className="settings-row">
        Scene
        <select value={sceneId} onChange={(e) => setSceneId(e.target.value)}>
          {scenes.map((s) => (
            <option key={s.sceneId} value={s.sceneId}>
              {s.locationName}
            </option>
          ))}
        </select>
      </label>
      <textarea
        className="char-draft-brief"
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Facts visible on the briefing board at this location…"
      />
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
      {msg && <p className="settings-muted">{msg}</p>}
    </section>
  );
}
