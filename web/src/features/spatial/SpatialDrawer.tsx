import type { SpatialGraph } from "../../api/client";
import { Drawer } from "../../ui/Drawer";
import { SpatialPanel } from "./SpatialPanel";
import type { ExitItem } from "./ExitList";

type Props = {
  open: boolean;
  onClose: () => void;
  graph: SpatialGraph | null;
  exits: ExitItem[];
  highlightedExitId: string | null;
  onTravel: (targetSceneId: string) => void;
  onKnock: (targetSceneId: string) => void;
  onExitHover: (exitId: string | null) => void;
  onMapOpen?: () => void;
  onOpenFullMap?: () => void;
  onMinimapSelect?: (sceneId: string) => void;
};

export function SpatialDrawer({
  open,
  onClose,
  graph,
  exits,
  highlightedExitId,
  onTravel,
  onKnock,
  onExitHover,
  onMapOpen,
  onOpenFullMap,
  onMinimapSelect,
}: Props) {
  return (
    <Drawer open={open} onClose={onClose} testId="spatial-drawer">
      <div id="spatial-drawer" className="spatial-drawer__content">
        {onMapOpen && (
          <button type="button" className="spatial-drawer__map-open" onClick={onMapOpen}>
            Open full world map
          </button>
        )}
        <SpatialPanel
          graph={graph}
          exits={exits}
          highlightedExitId={highlightedExitId}
          onTravel={onTravel}
          onKnock={onKnock}
          onExitHover={onExitHover}
          onOpenFullMap={onOpenFullMap ?? onMapOpen}
          onMinimapSelect={onMinimapSelect}
        />
      </div>
    </Drawer>
  );
}
