import { MiniMap } from "./MiniMap";
import type { SpatialGraph } from "../api/client";

type Props = {
  graph: SpatialGraph | null;
  onClose: () => void;
};

/** Site-scale world map (Phase 6a) — structured layout with structure list. */
export function WorldMapCanvas({ graph, onClose }: Props) {
  const structures = graph?.structures ?? [];
  return (
    <div className="map-overlay map-canvas" role="dialog" aria-label="World map canvas">
      <header className="map-overlay-header">
        <h2>World map</h2>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </header>
      <div className="map-canvas-body">
        <div className="map-canvas-main">
          <MiniMap graph={graph} />
        </div>
        {structures.length > 0 && (
          <aside className="map-canvas-structures">
            <h3>Structures</h3>
            <ul>
              {structures.map((s) => (
                <li key={s.structureId}>
                  {s.displayName}
                  {s.containsActiveScene ? " (active)" : ""}
                </li>
              ))}
            </ul>
          </aside>
        )}
      </div>
    </div>
  );
}
