import { useCallback, useEffect, useRef, useState } from "react";
import { SettingsPanel } from "./components/SettingsPanel";
import { MemoryInspector } from "./components/MemoryInspector";
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
import { PhonePanel } from "./components/PhonePanel";
import { PeopleRail } from "./components/PeopleRail";
import { SignalsRail } from "./components/SignalsRail";
import { ObserverDigest } from "./components/ObserverDigest";
import { CharacterDraftPanel } from "./components/CharacterDraftPanel";
import { DebatePanel } from "./components/DebatePanel";
import { MarkdownBody } from "./components/MarkdownBody";
import type { ObserverDigest as ObserverDigestData } from "./api/client";
import { LauncherView } from "./layouts/LauncherView";
import { SpatialShell } from "./layouts/SpatialShell";
import { Button } from "./ui/Button";
import type { ExitItem } from "./features/spatial/ExitList";

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
  const [observerDigest, setObserverDigest] = useState<ObserverDigestData | null>(null);
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
  const [mapOpen, setMapOpen] = useState(false);
  const [layoutDesignMode, setLayoutDesignMode] = useState(true);
  const sendInFlight = useRef(false);

  useEffect(() => {
    if (!world) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "m" || e.key === "M") {
        const t = e.target as HTMLElement;
        if (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable) return;
        e.preventDefault();
        setMapOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [world]);

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
    api.geography(w.worldId).then((g) => setLayoutDesignMode(g.layoutDesignMode)).catch(() => {});
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

  const createArchitectWorld = async () => {
    setLoading(true);
    try {
      const w = await api.createBlankWorld("Untitled world");
      const full = await api.getWorld(w.worldId);
      setWorld(full);
      await refresh(full);
    } finally {
      setLoading(false);
    }
  };

  const switchScene = async (sceneId: string) => {
    if (!world || sceneId === world.activeSceneId) return;
    const active = world.activeSceneId;
    let mode: "route" | "jump" = "route";
    if (graph && active) {
      const adj = graph.edges.some(
        (e) =>
          (e.sourceSceneId === active && e.targetSceneId === sceneId) ||
          (e.sourceSceneId === sceneId && e.targetSceneId === active)
      );
      if (!adj) {
        try {
          const summary = await api.navigationSummary(world.worldId, active);
          mode = summary.travelMode === "operator" ? "jump" : "route";
        } catch {
          mode = "jump";
        }
      }
    }
    try {
      const result = await api.navigationTravel(world.worldId, {
        toSceneId: sceneId,
        fromSceneId: active,
        mode,
      });
      const w = { ...world, activeSceneId: result.activeSceneId };
      setWorld(w);
      await refresh(w);
    } catch {
      if (mode === "route") {
        try {
          const result = await api.navigationTravel(world.worldId, {
            toSceneId: sceneId,
            fromSceneId: active,
            mode: "jump",
          });
          const w = { ...world, activeSceneId: result.activeSceneId };
          setWorld(w);
          await refresh(w);
        } catch {
          /* unreachable */
        }
      }
    }
  };

  const send = async () => {
    if (!world || !scene || !text.trim() || loading || sendInFlight.current) return;
    sendInFlight.current = true;
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
      sendInFlight.current = false;
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
    const result = await api.navigationTravel(world.worldId, {
      toSceneId: targetSceneId,
      fromSceneId: world.activeSceneId,
      mode: "route",
    });
    const w = { ...world, activeSceneId: result.activeSceneId };
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
        payload.event === "scene.created" ||
        payload.event === "commission.updated" ||
        payload.event === "signal.created" ||
        payload.event === "signal.updated" ||
        payload.event.startsWith("channel.") ||
        payload.event === "approval.updated"
      ) {
        refresh(world);
      }
    });
  }, [world, refresh]);

  useEffect(() => {
    if (observerOpen && world) {
      api.metaMessages(world.worldId).then(setMetaMessages);
      api.observerDigest(world.worldId).then(setObserverDigest).catch(() => setObserverDigest(null));
    }
  }, [observerOpen, world]);

  if (!world) {
    return (
      <LauncherView
        loading={loading}
        savedWorlds={savedWorlds}
        onLoadDemo={loadDemo}
        onCreateArchitect={createArchitectWorld}
        onOpenWorld={openWorld}
      />
    );
  }

  const sceneLabel = (id: string) =>
    scenes.find((s) => s.sceneId === id)?.locationName ?? id.replace("scene-", "");

  const pendingForScene = signals.filter((s) => s.targetSceneId === scene?.sceneId);
  const rawExits = scene ? JSON.parse(scene.exitsJson || "[]") : [];
  const exits: ExitItem[] = rawExits.map(
    (ex: { exitId: string; label: string; targetSceneId: string; direction?: string }) => ({
      exitId: ex.exitId,
      label: ex.label,
      targetSceneId: ex.targetSceneId,
      direction: ex.direction,
    })
  );

  const allPeople = [
    ...(roster?.atLocation ?? []),
    ...(roster?.elsewhere ?? []),
    ...(roster?.unplaced ?? []),
  ];

  const signalToast =
    pendingForScene.length > 0 ? (
      <div className="signal-toast signal-banner" data-testid="signal-toast">
        <span>
          Knock from {sceneLabel(pendingForScene[0].sourceSceneId)} ({pendingForScene[0].kind})
        </span>
        <div className="signal-toast__actions">
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              const who =
                roster?.atLocation.find((c) => c.characterId !== "__persona__") ??
                roster?.atLocation[0];
              if (!who) return;
              await api.answerSignal(world.worldId, pendingForScene[0].signalId, {
                characterId: who.characterId,
                targetSceneId: scene?.sceneId,
              });
              await refresh(world);
            }}
          >
            Answer (
            {roster?.atLocation.find((c) => c.characterId !== "__persona__")?.displayName ??
              "cast"}
            )
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              await api.dismissSignal(world.worldId, pendingForScene[0].signalId);
              await refresh(world);
            }}
          >
            Dismiss
          </Button>
        </div>
      </div>
    ) : null;

  return (
    <>
      <SpatialShell
        world={world}
        scene={scene}
        scenes={scenes}
        messages={messages}
        graph={graph}
        queue={queue}
        worldPaused={worldPaused}
        currentJobId={currentJobId}
        exits={exits}
        rosterAtLocation={roster?.atLocation ?? []}
        mapOpen={mapOpen}
        layoutDesignMode={layoutDesignMode}
        compose={{
          text,
          scope,
          loading,
          phoneChannelId,
          whisperTarget,
          people: allPeople,
          onTextChange: setText,
          onScopeChange: setScope,
          onWhisperTargetChange: setWhisperTarget,
          onSend: send,
        }}
        signalToast={signalToast}
        rightRail={
          <>
            {roster && scene && (
              <PeopleRail
                worldId={world.worldId}
                activeSceneId={scene.sceneId}
                scenes={scenes.map((s) => ({
                  sceneId: s.sceneId,
                  locationName: s.locationName,
                }))}
                roster={roster}
                onMemory={(characterId, displayName) =>
                  setMemoryFor({ characterId, displayName })
                }
                onPresenceChanged={() => refresh(world)}
              />
            )}
            {roster && scene && (
              <SignalsRail
                worldId={world.worldId}
                activeSceneId={scene.sceneId}
                signals={signals}
                castAtActive={roster.atLocation}
                sceneLabel={sceneLabel}
                onChanged={() => refresh(world)}
              />
            )}
          </>
        }
        onPauseToggle={async () => {
          if (worldPaused) await api.resumeWorld(world.worldId);
          else await api.pauseWorld(world.worldId);
          const w2 = await api.getWorld(world.worldId);
          setWorld(w2);
          setWorldPaused(!!w2.paused);
          await refresh(w2);
        }}
        onMapOpen={() => setMapOpen(true)}
        onMapClose={() => setMapOpen(false)}
        onEnhanceLayout={() => setMapOpen(true)}
        onObserver={() => setObserverOpen(true)}
        onSettings={async () => {
          await refresh(world);
          setSettingsOpen(true);
        }}
        onCancelJob={
          currentJobId
            ? async () => {
                await api.cancelJob(currentJobId);
                setCurrentJobId(null);
                await refresh(world);
              }
            : undefined
        }
        onSwitchScene={switchScene}
        onTravelExit={movePersonaToExit}
        onKnock={knock}
        onGraphRefresh={() => refresh(world)}
        onWorldRefresh={() => refresh(world)}
        toolsPhone={
          world && scene && roster ? (
            <PhonePanel
              worldId={world.worldId}
              activeSceneId={scene.sceneId}
              atLocation={roster.atLocation}
              elsewhere={roster.elsewhere}
              onChannelChange={() => refresh(world)}
            />
          ) : null
        }
        toolsDebate={
          world && scene && roster ? (
            <DebatePanel
              worldId={world.worldId}
              scene={scene}
              castIds={[
                ...roster.atLocation.map((c) => c.characterId),
                ...roster.elsewhere.map((c) => c.characterId),
              ]}
              charName={(id) => {
                const all = [...roster.atLocation, ...roster.elsewhere];
                return all.find((c) => c.characterId === id)?.displayName ?? id;
              }}
              onChanged={() => refresh(world)}
            />
          ) : null
        }
      />

      {settingsOpen && (
        <SettingsPanel
          worldId={world.worldId}
          worldName={world.name}
          worldPaused={worldPaused}
          onClose={() => setSettingsOpen(false)}
          onWorldImported={async (w) => {
            const full = await api.getWorld(w.worldId);
            setWorld(full);
            await refresh(full);
          }}
          onCastChanged={async () => {
            await refresh(world);
          }}
          scenes={scenes}
          onScenesChanged={async () => {
            await refresh(world);
          }}
          activeSceneId={world.activeSceneId}
        />
      )}

      {memoryFor && (
        <MemoryInspector
          worldId={world.worldId}
          characterId={memoryFor.characterId}
          displayName={memoryFor.displayName}
          onClose={() => setMemoryFor(null)}
        />
      )}

      {observerOpen && (
        <div className="observer-overlay" role="dialog" aria-label="Observer Studio" data-testid="observer-studio">
          <header className="top-bar">
            <h1>Observer Studio</h1>
            <Button variant="ghost" size="sm" onClick={() => setObserverOpen(false)}>
              Esc — Close
            </Button>
          </header>
          <aside className="observer-sidebar">
              <ObserverDigest
                digest={observerDigest}
                worldId={world.worldId}
                onRefresh={async () => {
                  setObserverDigest(await api.observerDigest(world.worldId));
                }}
              />
              <CharacterDraftPanel
                variant="observer"
                worldId={world.worldId}
                onCharacterAdded={async () => {
                  await refresh(world);
                  setObserverDigest(await api.observerDigest(world.worldId));
                }}
              />
          </aside>
            <div className="transcript observer-meta-scroll">
              {metaMessages.map((m) => (
                <article key={m.messageId} className="bubble chronicle-entry">
                  <div className="chronicle-entry__header">
                    <span className="chronicle-entry__speaker">{m.role}</span>
                  </div>
                  <MarkdownBody>{m.outputText}</MarkdownBody>
                </article>
              ))}
            </div>
            <footer className="compose persona-compose">
              <div className="persona-compose__row">
                <textarea
                  value={metaText}
                  onChange={(e) => setMetaText(e.target.value)}
                  placeholder="Meta channel…"
                />
                <Button
                  variant="primary"
                  onClick={async () => {
                    if (!metaText.trim()) return;
                    await api.postMeta(world.worldId, metaText.trim());
                    setMetaText("");
                    setMetaMessages(await api.metaMessages(world.worldId));
                  }}
                >
                  Send
                </Button>
              </div>
            </footer>
        </div>
      )}
    </>
  );
}
