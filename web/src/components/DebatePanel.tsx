import { useEffect, useState } from "react";
import { api, parseDebateActivity, type DebateActivity, type Scene } from "../api/client";

type Props = {
  worldId: string;
  scene: Scene;
  castIds: string[];
  charName: (id: string) => string;
  onChanged: () => void;
};

export function DebatePanel({ worldId, scene, castIds, charName, onChanged }: Props) {
  const [activity, setActivity] = useState<DebateActivity | null>(parseDebateActivity(scene));
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setActivity(parseDebateActivity(scene));
  }, [scene.activityJson]);

  useEffect(() => {
    if (castIds.length && selected.length === 0) {
      setSelected(castIds.filter((c) => c !== "__persona__").slice(0, 2));
    }
  }, [castIds]);

  const refreshDebate = async () => {
    const d = await api.getDebate(worldId, scene.sceneId);
    setActivity(d.activity);
  };

  const currentSpeaker =
    activity && activity.speakingOrder[activity.currentIndex]
      ? activity.speakingOrder[activity.currentIndex]
      : null;

  return (
    <section className="debate-panel">
      <h3>Debate</h3>
      {!activity ? (
        <>
          <p className="settings-muted">Structured turns at this scene (DEB-2).</p>
          <ul className="debate-speaker-pick">
            {castIds
              .filter((c) => c !== "__persona__")
              .map((cid) => (
                <li key={cid}>
                  <label>
                    <input
                      type="checkbox"
                      checked={selected.includes(cid)}
                      onChange={(e) => {
                        if (e.target.checked) setSelected((s) => [...s, cid]);
                        else setSelected((s) => s.filter((x) => x !== cid));
                      }}
                    />
                    {charName(cid)}
                  </label>
                </li>
              ))}
          </ul>
          <button
            type="button"
            className="people-secondary"
            disabled={busy || selected.length < 1}
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                await api.startDebate(worldId, scene.sceneId, {
                  speakingOrder: selected,
                  phase: "opening",
                });
                await refreshDebate();
                onChanged();
              } catch (e) {
                setError(e instanceof Error ? e.message : "Start failed");
              } finally {
                setBusy(false);
              }
            }}
          >
            Start debate
          </button>
        </>
      ) : (
        <>
          <p className="debate-phase">
            Phase: <strong>{activity.phase}</strong>
            {currentSpeaker && (
              <>
                {" "}
                · Speaker: <strong>{charName(currentSpeaker)}</strong>
              </>
            )}
          </p>
          <div className="debate-actions">
            <button
              type="button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await api.advanceDebateSpeaker(worldId, scene.sceneId);
                  await refreshDebate();
                  onChanged();
                } finally {
                  setBusy(false);
                }
              }}
            >
              Next speaker
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await api.advanceDebatePhase(worldId, scene.sceneId);
                  await refreshDebate();
                  onChanged();
                } finally {
                  setBusy(false);
                }
              }}
            >
              Next phase
            </button>
            <button
              type="button"
              className="people-secondary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await api.endDebate(worldId, scene.sceneId);
                  setActivity(null);
                  onChanged();
                } finally {
                  setBusy(false);
                }
              }}
            >
              End debate
            </button>
          </div>
        </>
      )}
      {error && <p className="settings-muted" style={{ color: "var(--danger, #c44)" }}>{error}</p>}
    </section>
  );
}
