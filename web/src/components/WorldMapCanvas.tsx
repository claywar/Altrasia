import { SiteMapCanvas } from "../features/maps/SiteMapCanvas";
import type { SpatialGraph } from "../api/client";

type Props = {
  graph: SpatialGraph | null;
  worldId: string;
  onClose: () => void;
  onEnhanceLayout?: () => void;
  onSwitchScene?: (sceneId: string) => void;
  onTravel?: (targetSceneId: string) => void;
  onKnock?: (targetSceneId: string) => void;
  highlightedExitId?: string | null;
  onExitHover?: (exitId: string | null) => void;
  onGraphRefresh?: () => void;
};

/** Site-scale world map — tactical MapConsole. */
export function WorldMapCanvas(props: Props) {
  return <SiteMapCanvas {...props} />;
}
