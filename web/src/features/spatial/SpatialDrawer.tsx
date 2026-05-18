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
}: Props) {
  return (
    <Drawer open={open} onClose={onClose} testId="spatial-drawer">
      <div id="spatial-drawer" className="spatial-drawer__content">
        <SpatialPanel
          graph={graph}
          exits={exits}
          highlightedExitId={highlightedExitId}
          onTravel={onTravel}
          onKnock={onKnock}
          onExitHover={onExitHover}
        />
      </div>
    </Drawer>
  );
}
