import type { NavigationRoute, SpatialGraph } from "../../api/client";
import { destinationsFromActive } from "../maps/mapNavigation";

type Props = {
  graph: SpatialGraph;
  selectedSceneId: string | null;
  route: NavigationRoute | null;
  routeLoading: boolean;
  onTravel: (sceneId: string) => void;
  onWalkRoute?: (sceneId: string) => void | Promise<void>;
  onKnock?: (sceneId: string) => void;
};

export function Map3DInspector({
  graph,
  selectedSceneId,
  route,
  routeLoading,
  onTravel,
  onWalkRoute,
  onKnock,
}: Props) {
  const active = graph.nodes.find((n) => n.isActive);
  const selected = graph.nodes.find((n) => n.sceneId === selectedSceneId);
  const destinations = destinationsFromActive(graph);

  return (
    <aside className="map3d-inspector" data-testid="map3d-inspector">
      <h3 className="map3d-inspector__title">Navigation</h3>
      {active && (
        <YouBlock label="You are here" value={active.locationName} />
      )}
      {selected && selected.sceneId !== active?.sceneId && (
        <YouBlock label="Selected" value={selected.locationName} />
      )}
      {routeLoading && <p className="map3d-inspector__hint">Planning route…</p>}
      {route && !route.reachable && selected && (
        <p className="map3d-inspector__warn">No path via exits to this location.</p>
      )}
      {route?.reachable && route.steps.length > 0 && (
        <div className="map3d-inspector__route">
          <span className="map3d-inspector__label">Route</span>
          <ol>
            {route.steps.map((s, i) => (
              <li key={s.exitId ?? i}>
                {s.label ?? s.toSceneId} ({s.travelSteps ?? 1} step
                {(s.travelSteps ?? 1) === 1 ? "" : "s"})
              </li>
            ))}
          </ol>
          <p className="map3d-inspector__meta">{route.totalTravelSteps} total steps</p>
        </div>
      )}
      {selected && selected.sceneId !== active?.sceneId && route?.reachable && (
        <div className="map3d-inspector__actions">
          {route.steps.length > 1 && onWalkRoute && (
            <button
              type="button"
              className="map3d-inspector__go"
              disabled={routeLoading}
              onClick={() => onWalkRoute(selected.sceneId)}
            >
              Walk route
            </button>
          )}
          <button
            type="button"
            className="map3d-inspector__go map3d-inspector__go--secondary"
            disabled={routeLoading}
            onClick={() => onTravel(selected.sceneId)}
          >
            {route.steps.length > 1 ? "Go now" : "Go"}
          </button>
        </div>
      )}
      <h4 className="map3d-inspector__section">Nearby exits</h4>
      <ul className="map3d-inspector__list">
        {destinations.map((d) => (
          <li key={d.exitId}>
            <button type="button" onClick={() => onTravel(d.targetSceneId)}>
              {d.label} → {d.targetName}
            </button>
            {onKnock && (
              <button
                type="button"
                className="map3d-inspector__knock"
                onClick={() => onKnock(d.targetSceneId)}
              >
                Knock
              </button>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
}

function YouBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="map3d-inspector__you">
      <span className="map3d-inspector__label">{label}</span>
      <span className="map3d-inspector__name">{value}</span>
    </div>
  );
}
