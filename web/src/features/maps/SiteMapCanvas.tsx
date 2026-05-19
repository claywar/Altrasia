import { MapConsole } from "./MapConsole";
import type { SpatialGraph } from "../../api/client";

type Props = {
  graph: SpatialGraph | null;
  worldId: string;
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

/** Full-screen tactical map console (Phase 6). */
export function SiteMapCanvas(props: Props) {
  return <MapConsole {...props} />;
}
