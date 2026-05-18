import type { SpatialGraph } from "../../api/client";
import { MiniMap } from "../../components/MiniMap";
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
};

/** Mini-map + exits — used in the persistent left column and the mobile drawer. */
export function SpatialPanel({
  graph,
  exits,
  highlightedExitId,
  onTravel,
  onKnock,
  onExitHover,
  onEnhanceLayout,
}: Props) {
  const activeNode = graph?.nodes.find((n) => n.isActive);
  const structure = graph?.structures?.find(
    (s) => s.structureId === activeNode?.structureId
  );
  const hasLayout =
    graph &&
    graph.nodes.length >= 2 &&
    graph.nodes.some((n) => n.layout && (n.layout.x !== 50 || n.layout.y !== 50));

  return (
    <div className="spatial-panel spatial-panel--framed" data-testid="spatial-panel">
      <MapPanelHeader
        structureName={structure?.displayName ?? activeNode?.structureId}
        mapZone={activeNode?.mapZone}
        sceneName={activeNode?.locationName}
      />
      {hasLayout ? (
        <MiniMap graph={graph} highlightedExitId={highlightedExitId} enablePan viewFit="full" />
      ) : (
        <div className="minimap minimap--empty">
          <p>Layout incomplete</p>
          {onEnhanceLayout && (
            <button type="button" className="minimap-empty-cta" onClick={onEnhanceLayout}>
              Enhance in Settings
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
