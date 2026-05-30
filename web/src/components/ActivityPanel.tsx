import { useEffect, useState } from "react";
import {
  api,
  parseSceneActivity,
  type Scene,
  type SceneActivity,
} from "../api/client";

type Props = {
  worldId: string;
  scene: Scene;
  castIds: string[];
  charName: (id: string) => string;
  onChanged: () => void;
};

type Tab = "debate" | "conversation" | "banter";

function SpeakerPick({
  castIds,
  charName,
  selected,
  onChange,
  min = 1,
}: {
  castIds: string[];
  charName: (id: string) => string;
  selected: string[];
  onChange: (ids: string[]) => void;
  min?: number;
}) {
  return (
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
                  if (e.target.checked) onChange([...selected, cid]);
                  else onChange(selected.filter((x) => x !== cid));
                }}
              />
              {charName(cid)}
            </label>
          </li>
        ))}
      {selected.length < min && (
        <p className="settings-muted">Select at least {min} speaker(s).</p>
      )}
    </ul>
  );
}

export function ActivityPanel({ worldId, scene, castIds, charName, onChanged }: Props) {
  const [tab, setTab] = useState<Tab>("debate");
  const [activity, setActivity] = useState<SceneActivity | null>(parseSceneActivity(scene));
  const [selected, setSelected] = useState<string[]>([]);
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setActivity(parseSceneActivity(scene));
  }, [scene.activityJson]);

  useEffect(() => {
    const cast = castIds.filter((c) => c !== "__persona__");
    if (cast.length && selected.length === 0) {
      setSelected(cast.slice(0, tab === "banter" ? 2 : 1));
    }
  }, [castIds, tab]);

  const refresh = async () => {
    if (tab === "debate") {
      const d = await api.getDebate(worldId, scene.sceneId);
      setActivity(d.activity);
    } else if (tab === "conversation") {
      const d = await api.getConversation(worldId, scene.sceneId);
      setActivity(d.activity);
    } else {
      const d = await api.getBanter(worldId, scene.sceneId);
      setActivity(d.activity);
    }
  };

  const activeForTab =
    activity && activity.kind === tab ? activity : null;

  const currentSpeaker =
    activeForTab && activeForTab.speakingOrder[activeForTab.currentIndex]
      ? activeForTab.speakingOrder[activeForTab.currentIndex]
      : null;

  const endActivity = async () => {
    setBusy(true);
    try {
      if (tab === "debate") await api.endDebate(worldId, scene.sceneId);
      else if (tab === "conversation") await api.endConversation(worldId, scene.sceneId);
      else await api.endBanter(worldId, scene.sceneId);
      setActivity(null);
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="debate-panel activity-panel">
      <h3>Scene activity</h3>
      <div className="activity-tabs" role="tablist">
        {(["debate", "conversation", "banter"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={tab === t ? "activity-tab active" : "activity-tab"}
            onClick={() => {
              setTab(t);
              setError(null);
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {!activeForTab ? (
        <>
          <p className="settings-muted">
            {tab === "debate" && "Structured debate turns (DEB-2)."}
            {tab === "conversation" && "Lightweight multi-speaker conversation (AO-22)."}
            {tab === "banter" && "Operator-started idle banter overlay."}
          </p>
          <SpeakerPick
            castIds={castIds}
            charName={charName}
            selected={selected}
            onChange={setSelected}
            min={tab === "banter" ? 2 : 1}
          />
          {tab === "conversation" && (
            <label className="settings-field">
              <span className="settings-field-label">Topic (optional)</span>
              <input type="text" value={topic} onChange={(e) => setTopic(e.target.value)} />
            </label>
          )}
          <button
            type="button"
            className="people-secondary"
            disabled={
              busy ||
              selected.length < (tab === "banter" ? 2 : 1)
            }
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                if (tab === "debate") {
                  await api.startDebate(worldId, scene.sceneId, {
                    speakingOrder: selected,
                    phase: "opening",
                  });
                } else if (tab === "conversation") {
                  await api.startConversation(worldId, scene.sceneId, {
                    speakingOrder: selected,
                    topic: topic.trim() || undefined,
                  });
                } else {
                  await api.startBanter(worldId, scene.sceneId, {
                    speakingOrder: selected,
                  });
                }
                await refresh();
                onChanged();
              } catch (e) {
                setError(e instanceof Error ? e.message : "Start failed");
              } finally {
                setBusy(false);
              }
            }}
          >
            Start {tab}
          </button>
        </>
      ) : (
        <>
          <p className="debate-phase">
            {activeForTab.kind === "debate" && (
              <>
                Phase: <strong>{activeForTab.phase}</strong>
              </>
            )}
            {activeForTab.kind === "conversation" && activeForTab.topic && (
              <>
                Topic: <strong>{activeForTab.topic}</strong>
              </>
            )}
            {activeForTab.kind === "banter" && (
              <>
                Turns left: <strong>{activeForTab.turnsRemaining ?? "—"}</strong>
              </>
            )}
            {currentSpeaker && (
              <>
                {" "}
                · Speaker: <strong>{charName(currentSpeaker)}</strong>
              </>
            )}
          </p>
          <div className="debate-actions">
            {(tab === "debate" || tab === "conversation") && (
              <button
                type="button"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    if (tab === "debate") {
                      await api.advanceDebateSpeaker(worldId, scene.sceneId);
                    } else {
                      await api.advanceConversationSpeaker(worldId, scene.sceneId);
                    }
                    await refresh();
                    onChanged();
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Next speaker
              </button>
            )}
            {tab === "debate" && (
              <button
                type="button"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await api.advanceDebatePhase(worldId, scene.sceneId);
                    await refresh();
                    onChanged();
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Next phase
              </button>
            )}
            <button type="button" className="people-secondary" disabled={busy} onClick={endActivity}>
              End {tab}
            </button>
          </div>
        </>
      )}
      {error && (
        <p className="settings-muted" style={{ color: "var(--danger, #c44)" }}>
          {error}
        </p>
      )}
    </section>
  );
}
