import { useState, type ReactNode } from "react";
import type { Scene, SpatialGraph, World } from "../api/client";
import { ApprovalsBanner } from "../components/ApprovalsBanner";
import { WorldMapOverlay } from "../components/WorldMapOverlay";
import { SceneStage } from "../features/scene/SceneStage";
import { ChronicleFeed } from "../features/transcript/ChronicleFeed";
import { PersonaCompose } from "../features/compose/PersonaCompose";
import { SpatialDrawer } from "../features/spatial/SpatialDrawer";
import { SpatialPanel } from "../features/spatial/SpatialPanel";
import type { ExitItem } from "../features/spatial/ExitList";
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
  graph: SpatialGraph | null;
  queue: QueueSnapshot;
  worldPaused: boolean;
  currentJobId: string | null;
  exits: ExitItem[];
  rosterAtLocation: RosterPerson[];
  mapOpen: boolean;
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
  toolsPhone: ReactNode;
  toolsDebate: ReactNode;
};

export function SpatialShell({
  world,
  scene,
  scenes,
  messages,
  graph,
  queue,
  worldPaused,
  currentJobId,
  exits,
  rosterAtLocation,
  mapOpen,
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
  toolsPhone,
  toolsDebate,
}: Props) {
  const [spatialOpen, setSpatialOpen] = useState(false);
  const [rightRailOpen, setRightRailOpen] = useState(true);
  const [highlightedExitId, setHighlightedExitId] = useState<string | null>(null);

  return (
    <div className="app-shell" data-testid="spatial-shell">
      <TopBar
        worldName={world.name}
        worldPaused={worldPaused}
        queue={queue}
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
          onClose={onMapClose}
          onEnhanceLayout={onEnhanceLayout}
          onSwitchScene={onSwitchScene}
          onTravel={onTravelExit}
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
            activeSceneId={world.activeSceneId}
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
      />
    </div>
  );
}
