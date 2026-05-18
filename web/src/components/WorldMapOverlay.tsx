import { MiniMap } from "./MiniMap";
import type { SpatialGraph } from "../api/client";

type Props = {
  graph: SpatialGraph | null;
  onClose: () => void;
};

export function WorldMapOverlay({ graph, onClose }: Props) {
  return (
    <div className="map-overlay" role="dialog" aria-label="World map">
      <header className="map-overlay-header">
        <h2>World map</h2>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </header>
      <div className="map-overlay-body">
        <MiniMap graph={graph} />
      </div>
    </div>
  );
}
