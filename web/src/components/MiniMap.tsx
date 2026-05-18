import { useMemo } from "react";
import { prepareGraphForView } from "../features/maps/floorLevels";
import { MapRenderer } from "../features/maps/MapRenderer";
import type { SpatialGraph } from "../api/client";
import type { MapGraph } from "../features/maps/types";

type Props = {
  graph: SpatialGraph | null;
  highlightedExitId?: string | null;
  className?: string;
  enablePan?: boolean;
  viewFit?: "neighborhood" | "full";
};

export function MiniMap({ graph, highlightedExitId, className, enablePan, viewFit }: Props) {
  const prepared = useMemo(() => {
    if (!graph) return null;
    return prepareGraphForView(graph as MapGraph, "site");
  }, [graph]);

  const displayGraph =
    prepared && graph
      ? ({
          ...graph,
          nodes: prepared.graph.nodes,
          edges: prepared.graph.edges,
        } as SpatialGraph)
      : graph;

  return (
    <MapRenderer
      graph={displayGraph}
      offPlanActive={prepared?.offPlanActive}
      highlightedExitId={highlightedExitId}
      className={className}
      enablePan={enablePan}
      viewFit={viewFit}
      showZoneBands={false}
    />
  );
}
