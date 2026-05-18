import { MapDraftPanel } from "../../components/MapDraftPanel";
import type { SpatialGraph } from "../../api/client";

type Props = {
  worldId: string;
  graph: SpatialGraph | null;
  onCommitted?: () => void;
};

/** Inline layout authoring inside MapConsole Author mode. */
export function MapAuthorPanel({ worldId, graph, onCommitted }: Props) {
  return (
    <div className="map-console-author">
      <h3>Layout author</h3>
      <p className="map-console-author__hint">
        Generate or repair layout drafts; commit applies positions to the world.
      </p>
      <MapDraftPanel worldId={worldId} graph={graph} onCommitted={onCommitted} embedded />
    </div>
  );
}
