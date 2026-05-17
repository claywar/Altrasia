import { useCallback, useEffect, useState } from "react";
import { MarkdownBody } from "./components/MarkdownBody";
import { GpuQueueStrip } from "./components/GpuQueueStrip";
import { SettingsPanel } from "./components/SettingsPanel";
import { MemoryInspector } from "./components/MemoryInspector";
import { MessageRationale } from "./components/MessageRationale";
import {
  api,
  connectWorldEvents,
  streamGeneration,
  type Message,
  type QueueSnapshot,
  type Scene,
  type SpatialGraph,
  type World,
} from "./api/client";
import { MiniMap } from "./components/MiniMap";
import { PhonePanel } from "./components/PhonePanel";

function parseScope(metaJson: string): string {
  try {
    return JSON.parse(metaJson).communication?.scope ?? "public";
  } catch {
    return "public";
  }
}

function parsePresent(raw: string): string[] {
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export default function App() {
  const [world, setWorld] = useState<World | null>(null);
  const [scene, setScene] = useState<Scene | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [graph, setGraph] = useState<SpatialGraph | null>(null);
  const [roster, setRoster] = useState<Awaited<ReturnType<typeof api.roster>> | null>(null);
  const [signals, setSignals] = useState<Awaited<ReturnType<typeof api.signals>>>([]);
  const [queue, setQueue] = useState<QueueSnapshot>({ busy: false, depth: 0 });
  const [text, setText] = useState("");
  const [scope, setScope] = useState("public");
  const [loading, setLoading] = useState(false);
  const [observerOpen, setObserverOpen] = useState(false);
  const [metaMessages, setMetaMessages] = useState<Message[]>([]);
  const [metaText, setMetaText] = useState("");
  const [whisperTarget, setWhisperTarget] = useState("");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [memoryFor, setMemoryFor] = useState<{
    characterId: string;
    displayName: string;
  } | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [worldPaused, setWorldPaused] = useState(false);
  const [savedWorlds, setSavedWorlds] = useState<World[]>([]);
  const [phoneChannelId, setPhoneChannelId] = useState<string | null>(null);

  useEffect(() => {
    if (!world) {
      api.listWorlds().then(setSavedWorlds).catch(() => setSavedWorlds([]));
    }
  }, [world]);

  const refresh = useCallback(async (w: World) => {
    const [scList, g, r, sig, q, chs] = await Promise.all([
      api.listScenes(w.worldId),
      api.spatialGraph(w.worldId),
      api.roster(w.worldId),
      api.signals(w.worldId),
      api.queue(w.worldId),
      api.listChannels(w.worldId).catch(() => []),
    ]);
    setPhoneChannelId(chs[0]?.channelId ?? null);
    setScenes(scList);
    setGraph(g);
    setRoster(r);
    setSignals(sig);
    setQueue(q);
    setWorldPaused(!!w.paused);
    const active = scList.find((s) => s.sceneId === w.activeSceneId) ?? scList[0];
    setScene(active);
    const msgs = await api.listMessages(w.worldId, active.sceneId);
    setMessages(msgs);
  }, []);

  const openWorld = async (w: World) => {
    setLoading(true);
    try {
      const full = await api.getWorld(w.worldId);
      setWorld(full);
      await refresh(full);
    } finally {
      setLoading(false);
    }
  };

  const loadDemo = async () => {
    setLoading(true);
    try {
      const w = await api.loadDemo();
      setWorld(w);
      await refresh(w);
    } finally {
      setLoading(false);
    }
  };

  const switchScene = async (sceneId: string) => {
    if (!world) return;
    await api.patchWorld(world.worldId, { activeSceneId: sceneId });
    const w = { ...world, activeSceneId: sceneId };
    setWorld(w);
    await refresh(w);
  };

  const send = async () => {
    if (!world || !scene || !text.trim()) return;
    setLoading(true);
    try {
      const participants =
        scope === "whisper" || scope === "dm"
          ? whisperTarget
            ? [whisperTarget]
            : []
          : [];
      const res = await api.sendMessage(world.worldId, scene.sceneId, {
        text: text.trim(),
        scope,
        participants,
        channelId: scope === "phone" ? phoneChannelId ?? undefined : undefined,
      });
      setText("");
      await refresh(world);
      if (res.generationJob?.jobId) {
        setCurrentJobId(res.generationJob.jobId);
        const q0 = await api.queue(world.worldId);
        setQueue(q0);
        streamGeneration(world.worldId, res.generationJob.jobId, async (ev) => {
          if (ev === "generation.done" || ev === "generation.error") {
            await refresh(world);
            const q = await api.queue(world.worldId);
            setQueue(q);
            setCurrentJobId(q.currentJob?.jobId ?? null);
          }
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const knock = async (targetSceneId: string) => {
    if (!world || !scene) return;
    await api.knock(world.worldId, {
      sourceSceneId: scene.sceneId,
      targetSceneId,
      kind: "knock",
    });
    await refresh(world);
  };

  const movePersonaToExit = async (targetSceneId: string) => {
    if (!world) return;
    await api.patchWorld(world.worldId, { activeSceneId: targetSceneId });
    const w = { ...world, activeSceneId: targetSceneId };
    setWorld(w);
    await refresh(w);
  };

  useEffect(() => {
    if (!world) return;
    return connectWorldEvents(world.worldId, (payload) => {
      if (payload.event === "queue.updated") {
        const d = payload.data as QueueSnapshot;
        setQueue({
          busy: !!d.busy,
          depth: d.depth ?? 0,
          estimatedWaitMs: d.estimatedWaitMs,
          currentJob: d.currentJob ?? null,
        });
        setCurrentJobId(d.currentJob?.jobId ?? null);
      }
      if (
        payload.event.startsWith("generation.") ||
        payload.event === "scene.changed" ||
        payload.event === "presence.changed" ||
        payload.event === "signal.created" ||
        payload.event === "signal.updated" ||
        payload.event.startsWith("channel.")
      ) {
        refresh(world);
      }
    });
  }, [world, refresh]);

  useEffect(() => {
    if (observerOpen && world) {
      api.metaMessages(world.worldId).then(setMetaMessages);
    }
  }, [observerOpen, world]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setObserverOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!world) {
    return (
      <div className="launcher">
        <h1>Altrasia</h1>
        <p className="launcher-tagline">
          Persistent stage for AI characters — memory-grounded, spatial, operator-run.
        </p>
        <button type="button" className="launcher-primary" onClick={loadDemo} disabled={loading}>
          {loading ? "Loading…" : "Load demo world"}
        </button>
        <p className="launcher-hint">demo-spatial-v1 · Hall + Kitchen · Alice &amp; Bob</p>
        <ol className="launcher-steps">
          <li>Public line in Hall → NPC reply</li>
          <li>Whisper one character · switch to Kitchen</li>
          <li>Knock on exit · Observer Studio for tweaks</li>
        </ol>
        {savedWorlds.length > 0 && (
          <div className="launcher-saved">
            <h2>Resume a world</h2>
            <ul>
              {savedWorlds.map((w) => (
                <li key={w.worldId}>
                  <button type="button" disabled={loading} onClick={() => openWorld(w)}>
                    {w.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  const sceneLabel = (id: string) =>
    scenes.find((s) => s.sceneId === id)?.locationName ?? id.replace("scene-", "");

  const pendingForScene = signals.filter((s) => s.targetSceneId === scene?.sceneId);
  const exits = scene ? JSON.parse(scene.exitsJson || "[]") : [];

  return (
    <div className="app-shell">
      <header className="top-bar">
        <h1>Altrasia — {world.name}</h1>
        <GpuQueueStrip
          busy={queue.busy}
          depth={queue.depth}
          estimatedWaitMs={queue.estimatedWaitMs}
          currentJob={queue.currentJob ?? undefined}
          onCancel={
            currentJobId
              ? async () => {
                  await api.cancelJob(currentJobId);
                  setCurrentJobId(null);
                  await refresh(world);
                }
              : undefined
          }
        />
        <button type="button" onClick={() => setObserverOpen(true)}>
          Observer Studio
        </button>
        <button type="button" onClick={() => setSettingsOpen(true)}>
          Settings
        </button>
        {worldPaused && <span className="paused-badge">Paused</span>}
      </header>

      {pendingForScene.length > 0 && (
        <div className="signal-banner">
          <span>
            Knock from {sceneLabel(pendingForScene[0].sourceSceneId)} ({pendingForScene[0].kind})
          </span>
          <button
            type="button"
            onClick={async () => {
              await api.answerSignal(world.worldId, pendingForScene[0].signalId, {
                characterId: "char-alice",
                targetSceneId: scene?.sceneId,
              });
              await refresh(world);
            }}
          >
            Answer (Alice)
          </button>
          <button
            type="button"
            onClick={async () => {
              await api.dismissSignal(world.worldId, pendingForScene[0].signalId);
              await refresh(world);
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="main-grid">
        <aside className="panel">
          <MiniMap graph={graph} />
          <div className="rail-section">
            <h3>Exits</h3>
            <ul className="rail-list">
              {exits.map(
                (ex: { exitId: string; label: string; targetSceneId: string }) => (
                  <li key={ex.exitId}>
                    <button
                      type="button"
                      style={{
                        background: "none",
                        border: "none",
                        color: "inherit",
                        cursor: "pointer",
                        padding: 0,
                        textAlign: "left",
                        width: "100%",
                      }}
                      onClick={() => movePersonaToExit(ex.targetSceneId)}
                    >
                      {ex.label}
                    </button>
                    <button
                      type="button"
                      style={{
                        marginLeft: 8,
                        fontSize: 11,
                        background: "var(--surface-3)",
                        border: "none",
                        color: "var(--muted)",
                        cursor: "pointer",
                        padding: "2px 6px",
                        borderRadius: 4,
                      }}
                      onClick={() => knock(ex.targetSceneId)}
                    >
                      Knock
                    </button>
                  </li>
                )
              )}
            </ul>
          </div>
        </aside>

        <main className="center">
          <header className="scene-header">
            <h2>{scene?.locationName}</h2>
            <p>{scene?.locationDescription}</p>
            <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
              Present: {scene ? parsePresent(scene.presentJson).join(", ") : "—"}
            </p>
          </header>
          <div className="transcript">
            {messages.map((m) => {
              const sc = parseScope(m.metaJson);
              const perceived = m.perceivedByPersona !== false;
              const label =
                m.role === "user"
                  ? "Persona"
                  : m.characterId?.replace("char-", "") ?? "NPC";
              return (
                <article
                  key={m.messageId}
                  className={`bubble ${sc} ${m.streamStatus === "streaming" ? "streaming" : ""} ${perceived ? "" : "dimmed"}`}
                  title={perceived ? undefined : "Not perceived at your position"}
                >
                  <div className="bubble-header">
                    {label} · {sc}
                    {m.role === "assistant" && m.generationJobId && (
                      <MessageRationale worldId={world.worldId} jobId={m.generationJobId} />
                    )}
                  </div>
                  <MarkdownBody>{m.outputText}</MarkdownBody>
                </article>
              );
            })}
          </div>
          <footer className="compose">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <select value={scope} onChange={(e) => setScope(e.target.value)}>
                <option value="public">Public</option>
                <option value="whisper">Whisper</option>
                <option value="dm">DM</option>
                {phoneChannelId && <option value="phone">Phone</option>}
              </select>
              {(scope === "whisper" || scope === "dm") && (
                <select
                  value={whisperTarget}
                  onChange={(e) => setWhisperTarget(e.target.value)}
                  aria-label="Whisper target"
                >
                  <option value="">Select character…</option>
                  {[...(roster?.atLocation ?? []), ...(roster?.elsewhere ?? [])].map((p) => (
                    <option key={p.characterId} value={p.characterId}>
                      {p.displayName}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="compose-row">
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Speak as persona…"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
              />
              <button type="button" onClick={send} disabled={loading}>
                Send
              </button>
            </div>
          </footer>
        </main>

        <aside className="panel right">
          <div className="rail-section">
            <h3>Places</h3>
            <ul className="rail-list">
              {scenes.map((s) => (
                <li
                  key={s.sceneId}
                  className={s.sceneId === world.activeSceneId ? "active" : ""}
                  onClick={() => switchScene(s.sceneId)}
                >
                  {s.locationName}
                </li>
              ))}
            </ul>
          </div>
          {world && scene && roster && (
            <PhonePanel
              worldId={world.worldId}
              activeSceneId={scene.sceneId}
              atLocation={roster.atLocation}
              elsewhere={roster.elsewhere}
              onChannelChange={() => refresh(world)}
            />
          )}
          <div className="rail-section">
            <h3>People</h3>
            <ul className="rail-list">
              {roster?.atLocation.map((p) => (
                <li key={p.characterId} className="people-row">
                  <span>{p.displayName} (here)</span>
                  <button
                    type="button"
                    className="people-memory"
                    onClick={() =>
                      setMemoryFor({ characterId: p.characterId, displayName: p.displayName })
                    }
                  >
                    Memory
                  </button>
                </li>
              ))}
              {roster?.elsewhere.map((p) => (
                <li key={p.characterId} className="people-row">
                  <span>
                    {p.displayName} — {p.locationName ?? "away"}
                  </span>
                  <button
                    type="button"
                    className="people-memory"
                    onClick={() =>
                      setMemoryFor({ characterId: p.characterId, displayName: p.displayName })
                    }
                  >
                    Memory
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="rail-section">
            <h3>Signals</h3>
            <ul className="rail-list">
              {signals.length === 0 && <li style={{ color: "var(--muted)" }}>None</li>}
              {signals.map((s) => (
                <li key={s.signalId}>
                  {s.kind}: {s.sourceSceneId} → {s.targetSceneId}
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>

      {settingsOpen && world && (
        <SettingsPanel
          worldId={world.worldId}
          worldName={world.name}
          worldPaused={worldPaused}
          onClose={() => setSettingsOpen(false)}
          onWorldPauseChange={async () => {
            const w2 = await api.getWorld(world.worldId);
            setWorld(w2);
            setWorldPaused(!!w2.paused);
            await refresh(w2);
          }}
          onWorldImported={async (w) => {
            const full = await api.getWorld(w.worldId);
            setWorld(full);
            await refresh(full);
          }}
        />
      )}

      {memoryFor && world && (
        <MemoryInspector
          worldId={world.worldId}
          characterId={memoryFor.characterId}
          displayName={memoryFor.displayName}
          onClose={() => setMemoryFor(null)}
        />
      )}

      {observerOpen && (
        <div className="observer-overlay" role="dialog" aria-label="Observer Studio">
          <header className="top-bar">
            <h1>Observer Studio</h1>
            <button type="button" onClick={() => setObserverOpen(false)}>
              Esc — Close
            </button>
          </header>
          <div className="transcript">
            {metaMessages.map((m) => (
              <article key={m.messageId} className="bubble">
                <div className="bubble-header">{m.role}</div>
                <p>{m.outputText}</p>
              </article>
            ))}
          </div>
          <footer className="compose">
            <div className="compose-row">
              <textarea
                value={metaText}
                onChange={(e) => setMetaText(e.target.value)}
                placeholder="Meta channel…"
              />
              <button
                type="button"
                onClick={async () => {
                  if (!world || !metaText.trim()) return;
                  await api.postMeta(world.worldId, metaText.trim());
                  setMetaText("");
                  setMetaMessages(await api.metaMessages(world.worldId));
                }}
              >
                Send
              </button>
            </div>
          </footer>
        </div>
      )}
    </div>
  );
}
