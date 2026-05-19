import { useMemo } from "react";
import type { SpatialGraph } from "../../api/client";
import {
  areAdjacentScenes,
  destinationsFromActive,
  directionGlyph,
  reachableSceneIdsFromGraph,
} from "../maps/mapNavigation";

type Props = {
  graph: SpatialGraph;
  selectedSceneId: string | null;
  onSelectScene: (sceneId: string) => void;
  onTravel: (sceneId: string) => void;
  onKnock?: (sceneId: string) => void;
};

export function MapTravelRail({
  graph,
  selectedSceneId,
  onSelectScene,
  onTravel,
  onKnock,
}: Props) {
  const activeId = graph.activeSceneId;
  const active = graph.nodes.find((n) => n.sceneId === activeId);

  const { nearby, elsewhere, byBuilding } = useMemo(() => {
    const adjacent = destinationsFromActive(graph);
    const adjacentIds = new Set(adjacent.map((d) => d.targetSceneId));
    const reachable = reachableSceneIdsFromGraph(graph);
    const elsewhereNodes = graph.nodes.filter(
      (n) =>
        n.sceneId !== activeId &&
        reachable.has(n.sceneId) &&
        !adjacentIds.has(n.sceneId)
    );

    const byBuilding = new Map<
      string,
      { structureId: string; name: string; rooms: typeof graph.nodes }
    >();
    for (const n of graph.nodes) {
      if (n.sceneId === activeId) continue;
      const sid = n.structureId ?? "_outdoor";
      const st = graph.structures?.find((s) => s.structureId === sid);
      const name = st?.displayName ?? (sid === "_outdoor" ? "Outdoors" : sid);
      if (!byBuilding.has(sid)) {
        byBuilding.set(sid, { structureId: sid, name, rooms: [] });
      }
      byBuilding.get(sid)!.rooms.push(n);
    }

    return { nearby: adjacent, elsewhere: elsewhereNodes, byBuilding: [...byBuilding.values()] };
  }, [graph, activeId]);

  return (
    <aside className="map-travel-rail" data-testid="map-travel-rail" aria-label="Travel">
      {active && (
        <div className="map-travel-rail__here">
          <span className="map-travel-rail__label">You are here</span>
          <strong>{active.locationName}</strong>
        </div>
      )}

      {nearby.length > 0 && (
        <section className="map-travel-rail__section">
          <h3>Nearby</h3>
          <ul>
            {nearby.map((d) => (
              <li key={d.exitId}>
                <button
                  type="button"
                  className="map-travel-rail__go"
                  onClick={() => onTravel(d.targetSceneId)}
                >
                  <span className="map-travel-rail__dir">{directionGlyph(d.direction)}</span>
                  <span>
                    <strong>{d.targetName}</strong>
                    <span className="map-travel-rail__via">via {d.label}</span>
                  </span>
                </button>
                {onKnock && (
                  <button
                    type="button"
                    className="map-travel-rail__knock"
                    onClick={() => onKnock(d.targetSceneId)}
                  >
                    Knock
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {elsewhere.length > 0 && (
        <section className="map-travel-rail__section">
          <h3>Elsewhere</h3>
          <ul>
            {elsewhere.map((n) => (
              <li key={n.sceneId}>
                <button
                  type="button"
                  className={
                    selectedSceneId === n.sceneId ? "map-travel-rail__pick map-travel-rail__pick--active" : "map-travel-rail__pick"
                  }
                  onClick={() => onSelectScene(n.sceneId)}
                >
                  {n.locationName}
                </button>
                <button
                  type="button"
                  className="map-travel-rail__go map-travel-rail__go--compact"
                  onClick={() => onTravel(n.sceneId)}
                >
                  Go
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="map-travel-rail__section map-travel-rail__section--buildings">
        <h3>Buildings</h3>
        {byBuilding.map((b) => (
          <details key={b.structureId} className="map-travel-rail__building" open={b.rooms.length <= 4}>
            <summary>{b.name}</summary>
            <ul>
              {b.rooms.map((n) => {
                const adj = areAdjacentScenes(graph, activeId, n.sceneId);
                const isHere = n.sceneId === activeId;
                if (isHere) return null;
                return (
                  <li key={n.sceneId}>
                    <button
                      type="button"
                      className={
                        selectedSceneId === n.sceneId
                          ? "map-travel-rail__pick map-travel-rail__pick--active"
                          : "map-travel-rail__pick"
                      }
                      onClick={() => onSelectScene(n.sceneId)}
                    >
                      {n.locationName}
                    </button>
                    {(adj || reachableSceneIdsFromGraph(graph).has(n.sceneId)) && (
                      <button
                        type="button"
                        className="map-travel-rail__go map-travel-rail__go--compact"
                        onClick={() => onTravel(n.sceneId)}
                      >
                        {adj ? "Go" : "Walk"}
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          </details>
        ))}
      </section>
    </aside>
  );
}
