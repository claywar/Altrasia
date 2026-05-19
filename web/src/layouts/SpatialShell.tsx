import { useCallback, useState, type ReactNode } from "react";
import { api, type Scene, SpatialGraph, World } from "../api/client";
import { ApprovalsBanner } from "../components/ApprovalsBanner";
import { WorldMapOverlay } from "../components/WorldMapOverlay";
import { SceneStage } from "../features/scene/SceneStage";
import { ChronicleFeed } from "../features/transcript/ChronicleFeed";
import { PersonaCompose } from "../features/compose/PersonaCompose";
import { SpatialDrawer } from "../features/spatial/SpatialDrawer";
import { SpatialPanel } from "../features/spatial/SpatialPanel";
import type { ExitItem } from "../features/spatial/ExitList";
import { areAdjacentScenes, reachableSceneIdsFromGraph } from "../features/maps/mapNavigation";
import { PlacesRail } from "../features/rails/PlacesRail";
import { ToolsRail } from "../features/rails/ToolsRail";
import { TopBar } from "./TopBar";
import type { Message, QueueSnapshot } from "../api/client";

type RosterPerson = {
  characterId: string;
  displayName: string;
  sceneId?: string | null;
  locationName?: string | null;
};

type Props = {
  world: World;
  scene: Scene | null;
  scenes: Scene[];
  messages: Message[];
  ambientActivity: Message[];
  ambientCharName: (characterId: string | null) => string;
  graph: SpatialGraph | null;
  queue: QueueSnapshot;
  worldPaused: boolean;
  currentJobId: string | null;
  exits: ExitItem[];
  rosterAtLocation: RosterPerson[];
  mapOpen: boolean;
  layoutDesignMode?: boolean;
  compose: {
    text: string;
    scope: string;
    loading: boolean;
    phoneChannelId: string | null;
    whisperTarget: string;
    people: RosterPerson[];
    onTextChange: (v: string) => void;
    onScopeChange: (v: string) => void;
    onWhisperTargetChange: (v: string) => void;
    onSend: () => void;
  };
  signalToast: ReactNode;
  rightRail: ReactNode;
  onPauseToggle: () => void;
  onMapOpen: () => void;
  onMapClose: () => void;
  onEnhanceLayout: () => void;
  onObserver: () => void;
  onSettings: () => void;
  onCancelJob?: () => void;
  onSwitchScene: (sceneId: string) => void;
  onTravelExit: (targetSceneId: string) => void;
  onKnock: (targetSceneId: string) => void;
  onGraphRefresh?: () => void;
  onWorldRefresh?: () => void | Promise<void>;
  toolsPhone: ReactNode;
  toolsDebate: ReactNode;
};

export function SpatialShell({
  world,
  scene,
  scenes,
  messages,
  ambientActivity,
  ambientCharName,
  graph,
  queue,
  worldPaused,
  currentJobId,
  exits,
  rosterAtLocation,
  mapOpen,
  layoutDesignMode = true,
  compose,
  signalToast,
  rightRail,
  onPauseToggle,
  onMapOpen,
  onMapClose,
  onEnhanceLayout,
  onObserver,
  onSettings,
  onCancelJob,
  onSwitchScene,
  onTravelExit,
  onKnock,
  onGraphRefresh,
  onWorldRefresh,
  toolsPhone,
  toolsDebate,
}: Props) {
  const [spatialOpen, setSpatialOpen] = useState(false);
  const [rightRailOpen, setRightRailOpen] = useState(true);
  const [highlightedExitId, setHighlightedExitId] = useState<string | null>(null);

  const handleMinimapSelect = (sceneId: string) => {
    if (!graph || sceneId === world.activeSceneId) return;
    if (areAdjacentScenes(graph, world.activeSceneId, sceneId)) {
      onTravelExit(sceneId);
    } else {
      onMapOpen();
    }
  };

  const walkRouteTo = useCallback(
    async (targetSceneId: string) => {
      if (!graph || targetSceneId === world.activeSceneId) return;
      let active = world.activeSceneId;
      for (let hops = 0; hops < 20 && active !== targetSceneId; hops++) {
        const result = await api.navigationTravel(world.worldId, {
          toSceneId: targetSceneId,
          fromSceneId: active,
          mode: "step",
        });
        if (result.route?.steps?.[0]?.exitId) {
          setHighlightedExitId(result.route.steps[0].exitId ?? null);
        }
        active = result.activeSceneId;
        if (active === world.activeSceneId) break;
        await onWorldRefresh?.();
      }
      setHighlightedExitId(null);
    },
    [graph, world, onSwitchScene, onWorldRefresh]
  );

  return (
    <div
      className={`app-shell${mapOpen ? " app-shell--map-focus" : ""}`}
      data-testid="spatial-shell"
    >
      <TopBar
        worldName={world.name}
        worldPaused={worldPaused}
        queue={queue}
        ambientActivity={ambientActivity}
        ambientCharName={ambientCharName}
        currentJobId={currentJobId}
        onPauseToggle={onPauseToggle}
        onMap={onMapOpen}
        onObserver={onObserver}
        onSettings={onSettings}
        onCancelJob={onCancelJob}
        onToggleRightRail={() => setRightRailOpen((v) => !v)}
        rightRailOpen={rightRailOpen}
      />
      <ApprovalsBanner worldId={world.worldId} />
      {mapOpen && (
        <WorldMapOverlay
          graph={graph}
          worldId={world.worldId}
          layoutDesignMode={layoutDesignMode}
          onClose={onMapClose}
          onEnhanceLayout={onEnhanceLayout}
          onSwitchScene={onSwitchScene}
          onTravel={onTravelExit}
          onWalkRoute={walkRouteTo}
          onKnock={onKnock}
          highlightedExitId={highlightedExitId}
          onExitHover={setHighlightedExitId}
          onGraphRefresh={onGraphRefresh}
        />
      )}
      {signalToast}
      <div className={`spatial-layout${rightRailOpen ? "" : " spatial-layout--rail-collapsed"}`}>
        <aside className="spatial-layout__left" aria-label="Spatial map and exits">
          <SpatialPanel
            graph={graph}
            exits={exits}
            highlightedExitId={highlightedExitId}
            onTravel={onTravelExit}
            onKnock={onKnock}
            onExitHover={setHighlightedExitId}
            onEnhanceLayout={onEnhanceLayout}
            onOpenFullMap={onMapOpen}
            onMinimapSelect={handleMinimapSelect}
          />
        </aside>
        <main className="spatial-layout__center" data-testid="center-column">
          <SceneStage
            scene={scene}
            graph={graph}
            rosterAtLocation={rosterAtLocation}
            spatialOpen={spatialOpen}
            onToggleSpatial={() => setSpatialOpen((v) => !v)}
            onMapOpen={onMapOpen}
          />
          <ChronicleFeed messages={messages} worldId={world.worldId} />
          <PersonaCompose {...compose} />
        </main>
        <aside
          className={`spatial-layout__rail${rightRailOpen ? "" : " spatial-layout__rail--hidden"}`}
          data-testid="right-rail"
        >
          <PlacesRail
            scenes={scenes}
            graph={graph}
            activeSceneId={world.activeSceneId}
            reachableSceneIds={
              graph ? reachableSceneIdsFromGraph(graph, world.activeSceneId) : undefined
            }
            onSelect={onSwitchScene}
          />
          {rightRail}
          <ToolsRail phone={toolsPhone} debate={toolsDebate} />
        </aside>
      </div>
      <SpatialDrawer
        open={spatialOpen}
        onClose={() => setSpatialOpen(false)}
        graph={graph}
        exits={exits}
        highlightedExitId={highlightedExitId}
        onTravel={(id) => {
          onTravelExit(id);
          setSpatialOpen(false);
        }}
        onKnock={onKnock}
        onExitHover={setHighlightedExitId}
        onMapOpen={() => {
          setSpatialOpen(false);
          onMapOpen();
        }}
        onOpenFullMap={onMapOpen}
        onMinimapSelect={handleMinimapSelect}
      />
    </div>
  );
}
