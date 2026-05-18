import { MapRenderer } from "../features/maps/MapRenderer";
import type { SpatialGraph } from "../api/client";

type Props = {
  graph: SpatialGraph | null;
  highlightedExitId?: string | null;
  className?: string;
  enablePan?: boolean;
  viewFit?: "neighborhood" | "full";
};

export function MiniMap({ graph, highlightedExitId, className, enablePan, viewFit }: Props) {
  return (
    <MapRenderer
      graph={graph}
      highlightedExitId={highlightedExitId}
      className={className}
      enablePan={enablePan}
      viewFit={viewFit}
    />
  );
}
