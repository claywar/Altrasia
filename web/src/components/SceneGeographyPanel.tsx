import { useEffect, useState } from "react";
import { api, type Scene } from "../api/client";

type Geography = {
  layoutDesignMode: boolean;
  geographyLockedAt: string | null;
  sceneCount: number;
};

type Props = {
  worldId: string;
  scenes: Scene[];
  onChanged: () => void;
};

export function SceneGeographyPanel({ worldId, scenes, onChanged }: Props) {
  const [geo, setGeo] = useState<Geography | null>(null);
  const [name, setName] = useState("");
  const [connectFrom, setConnectFrom] = useState("");
  const [exitLabel, setExitLabel] = useState("Door");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshGeo = () => api.geography(worldId).then(setGeo);

  useEffect(() => {
    refreshGeo();
    if (scenes[0] && !connectFrom) setConnectFrom(scenes[0].sceneId);
  }, [worldId, scenes.length]);

  const design = geo?.layoutDesignMode ?? false;

  return (
    <section className="settings-section">
      <h3>Scenes (Architect World)</h3>
      <p className="settings-muted">
        {design
          ? "Layout design mode — add scenes and exits, then lock geography before play."
          : geo?.geographyLockedAt
            ? `Geography locked · ${geo.sceneCount} scene(s)`
            : "Geography locked — scene graph is fixed for play."}
      </p>
      <ul className="scene-geo-list">
        {scenes.map((s) => (
          <li key={s.sceneId} className="scene-geo-row">
            <span>{s.locationName}</span>
            {design && scenes.length > 1 && (
              <button
                type="button"
                className="people-secondary"
                disabled={busy}
                onClick={async () => {
                  if (!confirm(`Delete scene "${s.locationName}"?`)) return;
                  setBusy(true);
                  setError(null);
                  try {
                    await api.deleteScene(worldId, s.sceneId);
                    onChanged();
                    await refreshGeo();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Delete failed");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Delete
              </button>
            )}
          </li>
        ))}
      </ul>
      {design && (
        <>
          <label className="settings-row">
            New location name
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Garden"
            />
          </label>
          <label className="settings-row">
            Connect from
            <select value={connectFrom} onChange={(e) => setConnectFrom(e.target.value)}>
              {scenes.map((s) => (
                <option key={s.sceneId} value={s.sceneId}>
                  {s.locationName}
                </option>
              ))}
            </select>
          </label>
          <label className="settings-row">
            Exit label
            <input
              type="text"
              value={exitLabel}
              onChange={(e) => setExitLabel(e.target.value)}
            />
          </label>
          <div className="settings-actions">
            <button
              type="button"
              disabled={busy || !name.trim()}
              onClick={async () => {
                setBusy(true);
                setError(null);
                try {
                  await api.createScene(worldId, {
                    locationName: name.trim(),
                    connectFromSceneId: connectFrom || undefined,
                    exitLabel: exitLabel.trim() || "Door",
                  });
                  setName("");
                  onChanged();
                  await refreshGeo();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Create failed");
                } finally {
                  setBusy(false);
                }
              }}
            >
              Add scene
            </button>
            <button
              type="button"
              disabled={busy || scenes.length < 1}
              onClick={async () => {
                if (!confirm("Lock geography? You will not be able to add or delete scenes."))
                  return;
                setBusy(true);
                try {
                  await api.lockGeography(worldId);
                  await refreshGeo();
                } finally {
                  setBusy(false);
                }
              }}
            >
              Lock geography
            </button>
          </div>
        </>
      )}
      {error && <p className="settings-error">{error}</p>}
    </section>
  );
}
