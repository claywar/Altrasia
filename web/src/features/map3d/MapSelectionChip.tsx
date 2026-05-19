import type { NavigationRoute, SpatialGraph } from "../../api/client";
import { areAdjacentScenes } from "../maps/mapNavigation";

type Props = {
  graph: SpatialGraph;
  selectedSceneId: string | null;
  route: NavigationRoute | null;
  routeLoading: boolean;
  onTravel: (sceneId: string) => void;
  onWalkRoute?: (sceneId: string) => void | Promise<void>;
  onKnock?: (sceneId: string) => void;
  onClear: () => void;
};

export function MapSelectionChip({
  graph,
  selectedSceneId,
  route,
  routeLoading,
  onTravel,
  onWalkRoute,
  onKnock,
  onClear,
}: Props) {
  const activeId = graph.activeSceneId;
  const active = graph.nodes.find((n) => n.sceneId === activeId);
  const selected = graph.nodes.find((n) => n.sceneId === selectedSceneId);

  if (!selected || selected.sceneId === activeId) {
    if (!active) return null;
    return (
      <div className="map-selection-chip map-selection-chip--here" data-testid="map-selection-chip">
        <span className="map-selection-chip__label">You are here</span>
        <strong>{active.locationName}</strong>
        {active.mapZone && <span className="map-selection-chip__meta">{active.mapZone}</span>}
      </div>
    );
  }

  const adjacent = areAdjacentScenes(graph, activeId, selected.sceneId);
  const reachable = route?.reachable ?? adjacent;
  const multiHop = route?.reachable && (route.steps?.length ?? 0) > 1;

  let primaryLabel = "Go";
  let primaryAction = () => onTravel(selected.sceneId);
  if (!adjacent && multiHop && onWalkRoute) {
    primaryLabel = "Walk there";
    primaryAction = () => onWalkRoute(selected.sceneId);
  }

  const exitToSelected = graph.edges.find(
    (e) => e.sourceSceneId === activeId && e.targetSceneId === selected.sceneId
  );

  return (
    <div className="map-selection-chip" data-testid="map-selection-chip" role="region" aria-label="Travel">
      <button type="button" className="map-selection-chip__dismiss" onClick={onClear} aria-label="Clear selection">
        ×
      </button>
      <div className="map-selection-chip__body">
        <span className="map-selection-chip__label">Destination</span>
        <strong>{selected.locationName}</strong>
        {routeLoading && <span className="map-selection-chip__meta">Planning route…</span>}
        {!routeLoading && route && !route.reachable && (
          <span className="map-selection-chip__warn">No path via exits</span>
        )}
        {!routeLoading && route?.reachable && multiHop && (
          <span className="map-selection-chip__meta">
            {route.totalTravelSteps} step{route.totalTravelSteps === 1 ? "" : "s"}
          </span>
        )}
      </div>
      {reachable && (
        <div className="map-selection-chip__actions">
          <button
            type="button"
            className="map-selection-chip__primary"
            disabled={routeLoading}
            onClick={primaryAction}
          >
            {primaryLabel}
          </button>
          {multiHop && onWalkRoute && !adjacent && (
            <button
              type="button"
              className="map-selection-chip__secondary"
              disabled={routeLoading}
              onClick={() => onTravel(selected.sceneId)}
            >
              Go now
            </button>
          )}
          {onKnock && exitToSelected && (
            <button type="button" className="map-selection-chip__link" onClick={() => onKnock(selected.sceneId)}>
              Knock
            </button>
          )}
        </div>
      )}
    </div>
  );
}
