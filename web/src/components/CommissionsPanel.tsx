import { useEffect, useState } from "react";
import { api, type Commission, type Scene } from "../api/client";

type Props = {
  worldId: string;
  scenes: Scene[];
};

export function CommissionsPanel({ worldId, scenes }: Props) {
  const [items, setItems] = useState<Commission[]>([]);
  const [cast, setCast] = useState<Array<{ characterId: string; displayName: string }>>([]);
  const [assignee, setAssignee] = useState("");
  const [targetScene, setTargetScene] = useState("");
  const [brief, setBrief] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useWebTools, setUseWebTools] = useState(false);

  const load = () => api.listCommissions(worldId).then(setItems).catch(() => setItems([]));

  useEffect(() => {
    load();
    api.listCharacters(worldId).then((rows) =>
      setCast(rows.map((r) => ({ characterId: r.characterId, displayName: r.displayName })))
    );
  }, [worldId]);

  useEffect(() => {
    if (cast[0] && !assignee) setAssignee(cast[0].characterId);
    if (scenes[0] && !targetScene) setTargetScene(scenes[0].sceneId);
  }, [cast, scenes]);

  const sceneName = (id: string) =>
    scenes.find((s) => s.sceneId === id)?.locationName ?? id;

  const charName = (id: string) =>
    cast.find((c) => c.characterId === id)?.displayName ?? id;

  return (
    <section className="settings-section">
      <h3>Commissions (schema)</h3>
      <p className="settings-muted">
        Assign errands; assignee must be at the target scene (COM-6). Start work or summon them
        there first.
      </p>
      <ul className="scene-geo-list commissions-list">
        {items.map((c) => (
          <li key={c.commissionId} className="commission-row">
            <div>
              <strong>{charName(c.assigneeCharacterId)}</strong> @ {sceneName(c.targetSceneId)}
              <span className={`commission-status status-${c.status}`}>{c.status}</span>
            </div>
            <p className="commission-brief">{c.brief}</p>
            {c.status === "queued" && (
              <button
                type="button"
                className="people-secondary"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError(null);
                  try {
                    await api.startCommission(worldId, c.commissionId);
                    await load();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Start failed");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Start work
              </button>
            )}
            {c.status === "blocked" && (
              <span className="settings-muted" style={{ fontSize: 11 }}>
                Waiting for assignee at scene
              </span>
            )}
            {(c.status === "queued" || c.status === "blocked" || c.status === "running") && (
              <button
                type="button"
                className="people-secondary"
                disabled={busy}
                onClick={async () => {
                  const reason = prompt("Force complete reason (COM-2 skip):");
                  if (!reason?.trim()) return;
                  setBusy(true);
                  try {
                    await api.patchCommission(worldId, c.commissionId, {
                      status: "done",
                      forceCompleteReason: reason.trim(),
                    });
                    await load();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Update failed");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Force complete
              </button>
            )}
          </li>
        ))}
        {items.length === 0 && <li style={{ color: "var(--muted)" }}>No commissions</li>}
      </ul>
      <label className="settings-row">
        Assignee
        <select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
          {cast.map((c) => (
            <option key={c.characterId} value={c.characterId}>
              {c.displayName}
            </option>
          ))}
        </select>
      </label>
      <label className="settings-row">
        Target scene
        <select value={targetScene} onChange={(e) => setTargetScene(e.target.value)}>
          {scenes.map((s) => (
            <option key={s.sceneId} value={s.sceneId}>
              {s.locationName}
            </option>
          ))}
        </select>
      </label>
      <label className="settings-row">
        <input
          type="checkbox"
          checked={useWebTools}
          onChange={(e) => setUseWebTools(e.target.checked)}
        />
        Allow web research (mock <code>webtools_invoke</code>)
      </label>
      <label className="settings-row">
        Brief
        <textarea
          className="char-draft-brief"
          rows={2}
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
          placeholder="What should they research or deliver?"
        />
      </label>
      <button
        type="button"
        disabled={busy || !brief.trim() || !assignee || !targetScene}
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            await api.createCommission(worldId, {
              assigneeCharacterId: assignee,
              targetSceneId: targetScene,
              brief: brief.trim(),
              allowedTools: useWebTools
                ? ["webtools_invoke", "memory_store", "memory_search", "memory_read"]
                : undefined,
            });
            setBrief("");
            await load();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Create failed");
          } finally {
            setBusy(false);
          }
        }}
      >
        Create commission
      </button>
      {error && <p className="settings-error">{error}</p>}
    </section>
  );
}
