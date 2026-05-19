import type { SpatialGraph } from "../../api/client";
import { SpatialCanvasPlay } from "./SpatialCanvasPlay";

type Props = {
  graph: SpatialGraph | null;
  worldId: string;
  layoutDesignMode?: boolean;
  onClose: () => void;
  onEnhanceLayout?: () => void;
  onSwitchScene?: (sceneId: string) => void;
  onTravel?: (targetSceneId: string) => void;
  onWalkRoute?: (targetSceneId: string) => void | Promise<void>;
  onKnock?: (targetSceneId: string) => void;
  highlightedExitId?: string | null;
  onExitHover?: (exitId: string | null) => void;
  onGraphRefresh?: () => void;
};

/** Full-screen play-first world map (3D primary). */
export function MapExplorer3D({
  graph,
  worldId,
  layoutDesignMode = true,
  onClose,
  onSwitchScene,
  onTravel,
  onWalkRoute,
  onKnock,
  onGraphRefresh,
  highlightedExitId,
  onExitHover,
}: Props) {
  return (
    <SpatialCanvasPlay
      graph={graph}
      worldId={worldId}
      layoutDesignMode={layoutDesignMode}
      onClose={onClose}
      onSwitchScene={onSwitchScene}
      onTravel={onTravel}
      onWalkRoute={onWalkRoute}
      onKnock={onKnock}
      highlightedExitId={highlightedExitId}
      onExitHover={onExitHover}
      onGraphRefresh={onGraphRefresh}
    />
  );
}
