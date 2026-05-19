import { useMemo } from "react";
import type { SpatialGraph } from "../../api/client";
import { buildSceneGraph3D } from "./buildSceneGraph";
import { EdgeTubes } from "./EdgeTubes";
import { RoomVolume } from "./RoomVolume";
import { StructureShell } from "./StructureShell";
import { WorldScene } from "./WorldScene";

type Props = {
  graph: SpatialGraph | null;
  className?: string;
  onSelect?: (sceneId: string) => void;
};

export function MiniMap3D({ graph, className, onSelect }: Props) {
  const sceneData = useMemo(() => (graph ? buildSceneGraph3D(graph, null) : null), [graph]);

  if (!graph || !sceneData?.rooms.length) {
    return (
      <div className={`minimap3d minimap3d--empty${className ? ` ${className}` : ""}`}>
        <p className="minimap3d__hint">No map layout yet.</p>
      </div>
    );
  }

  return (
    <div
      className={`minimap3d${className ? ` ${className}` : ""}`}
      data-testid="minimap-3d"
    >
      <WorldScene className="minimap3d__canvas" compact>
        <StructureShell structures={sceneData.structures} hideLabels />
        <RoomVolume
          rooms={sceneData.rooms}
          selectedSceneId={null}
          onSelect={(sceneId) => onSelect?.(sceneId)}
          labelActiveOnly
          hiddenWalls={sceneData.hiddenWalls}
        />
        <EdgeTubes edges={sceneData.edges} />
      </WorldScene>
    </div>
  );
}
