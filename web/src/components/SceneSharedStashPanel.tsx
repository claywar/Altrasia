import { useCallback, useEffect, useState } from "react";
import { api, type Scene } from "../api/client";
import { SettingsBlock } from "./settings/SettingsBlock";

type StashItem = { itemId: string; label: string };
type StashRecord = {
  label?: string;
  items?: StashItem[];
  capacity?: number;
};

type Props = {
  worldId: string;
  scenes: Scene[];
  activeSceneId: string;
  embedded?: boolean;
  onChanged?: () => void;
};

function parseStash(raw: string | undefined): Record<string, StashRecord> {
  try {
    return JSON.parse(raw || "{}") as Record<string, StashRecord>;
  } catch {
    return {};
  }
}

export function SceneSharedStashPanel({
  worldId,
  scenes,
  activeSceneId,
  embedded,
}: Props) {
  const [sceneId, setSceneId] = useState(activeSceneId);
  const [stash, setStash] = useState<Record<string, StashRecord>>({});

  const loadScene = useCallback(
    (sid: string) => {
      api
        .getScene(worldId, sid)
        .then((sc) => setStash(parseStash(sc.sharedStashJson)))
        .catch(() => setStash({}));
    },
    [worldId]
  );

  useEffect(() => {
    setSceneId(activeSceneId);
  }, [activeSceneId]);

  useEffect(() => {
    if (sceneId) loadScene(sceneId);
  }, [sceneId, loadScene]);

  const body = (
    <>
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
      <ul className="settings-list settings-list-plain">
        {Object.entries(stash).map(([key, entry]) => (
          <li key={key} className="settings-list-item">
            <div className="settings-list-text">
              <strong>{entry.label ?? key}</strong>
              <span className="settings-list-meta">
                {key} · {(entry.items ?? []).length}
                {entry.capacity != null ? ` / ${entry.capacity}` : ""} items
              </span>
            </div>
            <ul className="settings-list settings-list-plain">
              {(entry.items ?? []).map((item) => (
                <li key={item.itemId} className="settings-list-item">
                  {item.label}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
      {Object.keys(stash).length === 0 && (
        <p className="settings-muted">No shared stashes in this scene.</p>
      )}
    </>
  );

  if (embedded) {
    return (
      <SettingsBlock
        title="Shared stashes"
        description="Scene-bound group inventory pools (GS-1)."
      >
        {body}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section">
      <h3>Shared stashes</h3>
      {body}
    </section>
  );
}
