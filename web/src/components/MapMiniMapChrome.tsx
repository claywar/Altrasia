import type { SpatialGraph } from "../api/client";
import { mapViewCapabilities } from "../features/maps/mapNavigation";

type Props = {
  graph: SpatialGraph | null;
  onOpenFullMap?: () => void;
};

/** Hint strip under the sidebar mini-map — surfaces multi-floor / full map. */
export function MapMiniMapChrome({ graph, onOpenFullMap }: Props) {
  const caps = mapViewCapabilities(graph);
  if (!graph) return null;

  return (
    <div className="map-minimap-chrome">
      <p className="map-minimap-chrome__label">
        World map preview
        {caps.hasMultipleFloors && (
          <span className="map-minimap-chrome__floors"> · {caps.floorCount} floors</span>
        )}
      </p>
      {caps.personaOffSitePlan && (
        <p className="map-minimap-chrome__warn">
          You are on {caps.personaLevelLabel ?? "another level"} — not shown here.
        </p>
      )}
      {onOpenFullMap && (
        <button type="button" className="map-minimap-chrome__open" onClick={onOpenFullMap}>
          Open world map
        </button>
      )}
    </div>
  );
}
