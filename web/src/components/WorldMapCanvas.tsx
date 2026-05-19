import { MapExplorer3D } from "../features/map3d/MapExplorer3D";
import type { SpatialGraph } from "../api/client";

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

/** Site-scale world map — 3D explorer (primary) with diagram fallback inside. */
export function WorldMapCanvas(props: Props) {
  return <MapExplorer3D {...props} />;
}
