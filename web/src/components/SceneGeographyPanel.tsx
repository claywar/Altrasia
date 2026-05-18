import { useEffect, useState } from "react";
import { api, type Scene } from "../api/client";
import { SettingsBlock } from "./settings/SettingsBlock";

type Geography = {
  layoutDesignMode: boolean;
  geographyLockedAt: string | null;
  sceneCount: number;
};

type Props = {
  worldId: string;
  scenes: Scene[];
  onChanged: () => void;
  embedded?: boolean;
};

export function SceneGeographyPanel({ worldId, scenes, onChanged, embedded }: Props) {
  const [geo, setGeo] = useState<Geography | null>(null);
  const [name, setName] = useState("");
  const [connectFrom, setConnectFrom] = useState("");
  const [exitLabel, setExitLabel] = useState("Door");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshGeo = () => api.geography(worldId).then(setGeo);

  useEffect(() => {
    refreshGeo();
    if (scenes[0] && !connectFrom) setConnectFrom(scenes[0].sceneId);
  }, [worldId, scenes.length]);

  const design = geo?.layoutDesignMode ?? false;
  const locked = geo && !design;

  const addScene = async () => {
    if (!name.trim()) return;
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
  };

  const saveRename = async (sceneId: string) => {
    if (!editName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.patchScene(worldId, sceneId, { locationName: editName.trim() });
      setEditingId(null);
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rename failed");
    } finally {
      setBusy(false);
    }
  };

  const description = design
    ? "Layout design mode — add scenes and exits, then lock geography before play."
    : geo?.geographyLockedAt
      ? `Geography locked · ${geo.sceneCount} scene(s) · rename or add connected locations`
      : "Rename scenes or add locations linked by exits.";

  const body = (
    <>
      <ul className="scene-geo-list">
        {scenes.map((s) => (
          <li key={s.sceneId} className="scene-geo-row">
            {editingId === s.sceneId ? (
              <div className="scene-geo-rename">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") saveRename(s.sceneId);
                    if (e.key === "Escape") setEditingId(null);
                  }}
                />
                <button type="button" className="people-secondary" onClick={() => saveRename(s.sceneId)}>
                  Save
                </button>
              </div>
            ) : (
              <>
                <span>{s.locationName}</span>
                <div className="people-actions">
                  <button
                    type="button"
                    className="people-memory"
                    onClick={() => {
                      setEditingId(s.sceneId);
                      setEditName(s.locationName);
                    }}
                  >
                    Rename
                  </button>
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
                </div>
              </>
            )}
          </li>
        ))}
      </ul>
      {(design || locked) && (
        <>
          <p className="settings-muted">
            {locked ? "In-map growth: new location must connect from an existing scene." : null}
          </p>
          <label className="settings-row">
            {locked ? "New connected location" : "New location name"}
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
            <button type="button" disabled={busy || !name.trim()} onClick={addScene}>
              {locked ? "Add connected location" : "Add scene"}
            </button>
            {design && (
              <button
                type="button"
                disabled={busy || scenes.length < 1}
                onClick={async () => {
                  if (!confirm("Lock geography? You will not be able to delete scenes."))
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
            )}
          </div>
        </>
      )}
      {error && <p className="settings-error">{error}</p>}
    </>
  );

  if (embedded) {
    return (
      <SettingsBlock title="Scenes" description={description}>
        {body}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section">
      <h3>Scenes (Architect World)</h3>
      <p className="settings-muted">{description}</p>
      {body}
    </section>
  );
}
