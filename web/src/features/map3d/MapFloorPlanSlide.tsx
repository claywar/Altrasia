import type { SpatialGraph } from "../../api/client";
import { MapFloorPlanView } from "./MapFloorPlanView";

type Props = {
  graph: SpatialGraph;
  viewMode?: "site" | "building";
  selectedSceneId: string | null;
  onSelectScene: (sceneId: string) => void;
  onPatchPosition?: (sceneId: string, x: number, y: number) => void;
};

/** Full-screen floor plan (replaces 3D while active). */
export function MapFloorPlanSlide({
  graph,
  viewMode = "site",
  selectedSceneId,
  onSelectScene,
  onPatchPosition,
}: Props) {
  return (
    <div className="map-floor-plan-view-wrap" data-testid="map-floor-plan-slide">
      <MapFloorPlanView
        graph={graph}
        viewMode={viewMode}
        selectedSceneId={selectedSceneId}
        onSelectScene={onSelectScene}
        onPatchPosition={onPatchPosition}
      />
    </div>
  );
}
