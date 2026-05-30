import { useCallback, useEffect, useState } from "react";
import { api, type Scene } from "../api/client";
import { SettingsBlock } from "./settings/SettingsBlock";

type FixtureRecord = {
  label?: string;
  kind?: string;
  portable?: boolean;
  wearable?: boolean;
  picksRemaining?: number;
  defaultPicks?: number;
  description?: string;
  yield?: { label?: string };
};

type Props = {
  worldId: string;
  scenes: Scene[];
  activeSceneId: string;
  embedded?: boolean;
  onChanged?: () => void;
};

function parseFixtures(raw: string | undefined): Record<string, FixtureRecord> {
  try {
    return JSON.parse(raw || "{}") as Record<string, FixtureRecord>;
  } catch {
    return {};
  }
}

export function SceneFixturesPanel({
  worldId,
  scenes,
  activeSceneId,
  embedded,
  onChanged,
}: Props) {
  const [sceneId, setSceneId] = useState(activeSceneId);
  const [fixtures, setFixtures] = useState<Record<string, FixtureRecord>>({});
  const [saving, setSaving] = useState(false);

  const loadScene = useCallback(
    (sid: string) => {
      api
        .getScene(worldId, sid)
        .then((sc) => setFixtures(parseFixtures(sc.fixturesJson)))
        .catch(() => setFixtures({}));
    },
    [worldId]
  );

  useEffect(() => {
    setSceneId(activeSceneId);
  }, [activeSceneId]);

  useEffect(() => {
    if (sceneId) loadScene(sceneId);
  }, [sceneId, loadScene]);

  const save = async (next: Record<string, FixtureRecord>) => {
    setSaving(true);
    try {
      await api.patchScene(worldId, sceneId, { fixturesJson: JSON.stringify(next) });
      setFixtures(next);
      onChanged?.();
    } finally {
      setSaving(false);
    }
  };

  const updateFixture = (key: string, patch: Partial<FixtureRecord>) => {
    const next = { ...fixtures, [key]: { ...fixtures[key], ...patch } };
    void save(next);
  };

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
        {Object.entries(fixtures).map(([key, fix]) => (
          <li key={key} className="settings-list-item fixture-edit-row">
            <div className="settings-list-text">
              <strong>{fix.label ?? key}</strong>
              <span className="settings-list-meta">{key}</span>
            </div>
            <label className="settings-field settings-field-inline">
              <span>Kind</span>
              <select
                value={fix.kind ?? "discrete"}
                disabled={saving}
                onChange={(e) => updateFixture(key, { kind: e.target.value })}
              >
                <option value="discrete">discrete</option>
                <option value="aggregate">aggregate</option>
                <option value="briefing">briefing</option>
              </select>
            </label>
            {fix.kind === "aggregate" && (
              <label className="settings-field settings-field-inline">
                <span>Picks left</span>
                <input
                  type="number"
                  min={0}
                  value={fix.picksRemaining ?? 0}
                  disabled={saving}
                  onChange={(e) =>
                    updateFixture(key, { picksRemaining: Number(e.target.value) })
                  }
                />
              </label>
            )}
            {(fix.kind === "discrete" || fix.kind === "fixture" || !fix.kind) && (
              <label className="settings-field settings-field-inline">
                <span>Portable</span>
                <input
                  type="checkbox"
                  checked={fix.portable !== false}
                  disabled={saving}
                  onChange={(e) => updateFixture(key, { portable: e.target.checked })}
                />
              </label>
            )}
          </li>
        ))}
      </ul>
      {Object.keys(fixtures).length === 0 && (
        <p className="settings-muted">No fixtures in this scene.</p>
      )}
    </>
  );

  if (embedded) {
    return (
      <SettingsBlock title="Scene fixtures" description="Discrete and aggregate fixture records.">
        {body}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section">
      <h3>Scene fixtures</h3>
      {body}
    </section>
  );
}
