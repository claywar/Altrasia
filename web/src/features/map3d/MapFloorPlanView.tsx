import { useCallback, useEffect, useMemo, useRef } from "react";
import type { SpatialGraph } from "../../api/client";
import { MapRenderer } from "../maps/MapRenderer";
import {
  activeLevel,
  activeStructureId,
  prepareGraphForView,
  type MapViewMode,
} from "../maps/floorLevels";
import { useMapViewport } from "../maps/useMapViewport";
import type { MapGraph } from "../maps/types";

type Props = {
  graph: SpatialGraph;
  selectedSceneId: string | null;
  onSelectScene: (sceneId: string) => void;
  onPatchPosition?: (sceneId: string, x: number, y: number) => void;
  /** site = full map; building = active structure floor */
  viewMode?: "site" | "building";
};

export function MapFloorPlanView({
  graph,
  selectedSceneId,
  onSelectScene,
  onPatchPosition,
  viewMode = "site",
}: Props) {
  const mg = graph as MapGraph;
  const containerRef = useRef<HTMLDivElement>(null);
  const viewport = useMapViewport(graph);

  const diagramMode = useMemo((): MapViewMode => {
    if (viewMode === "site") return "site";
    return "floor";
  }, [viewMode]);

  const focusLevel = activeLevel(mg);
  const prepared = useMemo(
    () =>
      prepareGraphForView(mg, diagramMode, {
        selectedLevel: viewMode === "site" ? undefined : focusLevel,
      }),
    [mg, diagramMode, focusLevel, viewMode]
  );

  const displayGraph = useMemo(
    () =>
      ({
        ...graph,
        nodes: prepared.graph.nodes,
        edges: prepared.graph.edges,
        structures: prepared.graph.structures,
      }) as SpatialGraph,
    [graph, prepared]
  );

  const fitKey = `${viewMode}-${graph.activeSceneId}`;
  const lastFit = useRef("");
  useEffect(() => {
    if (lastFit.current === fitKey) return;
    lastFit.current = fitKey;
    if (viewMode === "site") viewport.fitSite();
    else {
      const structId = activeStructureId(mg);
      if (structId) viewport.fitStructure(structId);
      else viewport.fitSite();
    }
  }, [fitKey, viewMode, mg, viewport]);

  const handleSelect = useCallback(
    (sceneId: string) => onSelectScene(sceneId),
    [onSelectScene]
  );

  return (
    <div className="map-floor-plan-view" ref={containerRef}>
      <div
        className="map-floor-plan-view__viewport"
        tabIndex={0}
        onWheel={viewport.onWheel}
        onPointerDown={viewport.onPointerDown}
        onPointerMove={(e) => viewport.onPointerMove(e, containerRef.current)}
        onPointerUp={viewport.onPointerUp}
        onPointerLeave={viewport.onPointerUp}
      >
        <div
          className="site-map-transform"
          style={{
            transform: `translate(${viewport.pan.x}px, ${viewport.pan.y}px) scale(${viewport.zoom})`,
            transformOrigin: "center center",
          }}
        >
          <MapRenderer
            graph={displayGraph}
            offPlanActive={prepared.offPlanActive}
            className="site-map-main"
            viewFit="full"
            interactive
            showEnvelopes
            showEdges
            showLabels
            showZones={viewMode === "site"}
            showSiteUnderlay={viewMode === "site"}
            architectureStyle="diagram"
            selectedSceneId={selectedSceneId}
            onNodeSelect={handleSelect}
            onStructureSelect={(structureId) => {
              const first = mg.nodes.find(
                (n) => n.structureId === structureId && n.sceneId !== graph.activeSceneId
              );
              if (first) onSelectScene(first.sceneId);
            }}
            onNodePositionChange={
              onPatchPosition
                ? (sceneId, pos) => onPatchPosition(sceneId, pos.x, pos.y)
                : undefined
            }
          />
        </div>
      </div>
    </div>
  );
}
