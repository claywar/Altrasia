import type { SpatialGraph } from "../../api/client";
import { MapMiniMapChrome } from "../../components/MapMiniMapChrome";
import { MiniMap3D } from "../map3d/MiniMap3D";
import { MapPanelHeader } from "../maps/MapChrome";
import { ExitList, type ExitItem } from "./ExitList";

type Props = {
  graph: SpatialGraph | null;
  exits: ExitItem[];
  highlightedExitId: string | null;
  onTravel: (targetSceneId: string) => void;
  onKnock: (targetSceneId: string) => void;
  onExitHover: (exitId: string | null) => void;
  onEnhanceLayout?: () => void;
  onOpenFullMap?: () => void;
  onMinimapSelect?: (sceneId: string) => void;
};

/** Mini-map + exits — used in the persistent left column and the mobile drawer. */
export function SpatialPanel({
  graph,
  exits,
  highlightedExitId,
  onTravel,
  onKnock,
  onExitHover,
  onOpenFullMap,
  onMinimapSelect,
}: Props) {
  const activeNode = graph?.nodes.find((n) => n.isActive);
  const structure = graph?.structures?.find(
    (s) => s.structureId === activeNode?.structureId
  );
  const hasLayout =
    graph &&
    graph.nodes.length >= 2 &&
    (graph.layoutStatus === "complete" ||
      graph.layoutStatus === "partial" ||
      (!graph.layoutStatus &&
        graph.nodes.some((n) => n.layout && (n.layout.x !== 50 || n.layout.y !== 50))));

  return (
    <div className="spatial-panel spatial-panel--framed" data-testid="spatial-panel">
      <MapPanelHeader
        structureName={structure?.displayName ?? activeNode?.structureId}
        mapZone={activeNode?.mapZone}
        sceneName={activeNode?.locationName}
      />
      {hasLayout ? (
        <>
          <MiniMap3D graph={graph} onSelect={onMinimapSelect} />
          <MapMiniMapChrome graph={graph} onOpenFullMap={onOpenFullMap} />
        </>
      ) : (
        <div className="minimap minimap--empty">
          <p>Layout incomplete</p>
          {onOpenFullMap && (
            <button type="button" className="minimap-empty-cta" onClick={onOpenFullMap}>
              Open world map
            </button>
          )}
        </div>
      )}
      <ExitList
        exits={exits}
        highlightedExitId={highlightedExitId}
        onTravel={onTravel}
        onKnock={onKnock}
        onExitHover={onExitHover}
      />
    </div>
  );
}
