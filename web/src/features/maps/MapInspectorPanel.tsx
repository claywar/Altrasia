import { useEffect, useState } from "react";
import { api, type NavigationRoute, type SpatialGraph } from "../../api/client";
import { Button } from "../../ui/Button";
import { destinationsFromActive, directionGlyph } from "./mapNavigation";

export type MapSelection =
  | { type: "scene"; sceneId: string }
  | { type: "exit"; exitId: string }
  | { type: "structure"; structureId: string }
  | null;

type Props = {
  graph: SpatialGraph | null;
  worldId?: string;
  selection: MapSelection;
  activeSceneId: string;
  onSwitchScene?: (sceneId: string) => void;
  onTravel?: (targetSceneId: string) => void;
  onWalkRoute?: (targetSceneId: string) => void | Promise<void>;
  onKnock?: (targetSceneId: string) => void;
  onFitStructure?: (structureId: string) => void;
  onFitScene?: (sceneId: string) => void;
  onViewStructure?: () => void;
  onClearSelection?: () => void;
  onExitHover?: (exitId: string | null) => void;
  onSelectScene?: (sceneId: string) => void;
};

function NavigateHome({
  graph,
  activeSceneId,
  onTravel,
  onKnock,
  onExitHover,
  onSelectScene,
}: {
  graph: SpatialGraph;
  activeSceneId: string;
  onTravel?: (targetSceneId: string) => void;
  onKnock?: (targetSceneId: string) => void;
  onExitHover?: (exitId: string | null) => void;
  onSelectScene?: (sceneId: string) => void;
}) {
  const active = graph.nodes.find((n) => n.sceneId === activeSceneId);
  const destinations = destinationsFromActive(graph);

  return (
    <>
      <h3 className="map-console-inspector__section-title">Go somewhere</h3>
      {active && (
        <div className="map-console-inspector__you-are-here">
          <span className="map-console-inspector__you-label">You are here</span>
          <span className="map-console-inspector__you-name">{active.locationName}</span>
          {active.mapZone && (
            <span className="map-console-inspector__you-meta">{active.mapZone}</span>
          )}
        </div>
      )}

      {destinations.length > 0 ? (
        <>
          <p className="map-console-inspector__lead">
            Choose a destination — your persona will move there.
          </p>
          <ul className="map-console-destinations" aria-label="Destinations from current location">
            {destinations.map((d) => (
              <li key={d.exitId}>
                <div
                  className="map-console-destination"
                  onMouseEnter={() => onExitHover?.(d.exitId)}
                  onMouseLeave={() => onExitHover?.(null)}
                  onFocus={() => onExitHover?.(d.exitId)}
                  onBlur={() => onExitHover?.(null)}
                >
                  <button
                    type="button"
                    className="map-console-destination__main"
                    onClick={() => onTravel?.(d.targetSceneId)}
                  >
                    <span className="map-console-destination__dir" aria-hidden>
                      {directionGlyph(d.direction)}
                    </span>
                    <span className="map-console-destination__names">
                      <span className="map-console-destination__target">{d.targetName}</span>
                      <span className="map-console-destination__via">via {d.label}</span>
                    </span>
                    {d.travelSteps != null && d.travelSteps > 1 && (
                      <span className="map-console-destination__steps">{d.travelSteps} steps</span>
                    )}
                  </button>
                  <div className="map-console-destination__side">
                    {onKnock && (
                      <Button variant="ghost" size="sm" onClick={() => onKnock(d.targetSceneId)}>
                        Knock
                      </Button>
                    )}
                    {onSelectScene && (
                      <button
                        type="button"
                        className="map-console-destination__inspect"
                        onClick={() => onSelectScene(d.targetSceneId)}
                      >
                        Details
                      </button>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="map-console-inspector__lead">
          No exits from here. Click another building on the map or use Places in the right sidebar.
        </p>
      )}

      <details className="map-console-inspector__tips">
        <summary>How to use the map</summary>
        <ol>
          <li>Use the list above for the fastest way to travel.</li>
          <li>Or click a room or path on the map, then confirm in this panel.</li>
          <li>Drag to pan; scroll or use +/− to zoom. Press F to fit your building.</li>
          <li>Try Floor or Stack view (top tabs) when rooms span multiple levels.</li>
        </ol>
      </details>
    </>
  );
}

function SceneRouteActions({
  worldId,
  targetSceneId,
  activeSceneId,
  onTravel,
  onWalkRoute,
  onSwitchScene,
}: {
  worldId: string;
  targetSceneId: string;
  activeSceneId: string;
  onTravel?: (id: string) => void;
  onWalkRoute?: (id: string) => void | Promise<void>;
  onSwitchScene?: (id: string) => void;
}) {
  const [route, setRoute] = useState<NavigationRoute | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (targetSceneId === activeSceneId) {
      setRoute(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api
      .navigationRoute(worldId, activeSceneId, targetSceneId)
      .then((r) => {
        if (!cancelled) setRoute(r);
      })
      .catch(() => {
        if (!cancelled) setRoute(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [worldId, activeSceneId, targetSceneId]);

  const go = onTravel ?? onSwitchScene;
  if (!go) return null;

  if (loading) {
    return <p className="map-console-inspector__meta">Planning route…</p>;
  }
  if (route && !route.reachable) {
    return <p className="map-console-inspector__warn">No path via exits.</p>;
  }
  if (route?.reachable && route.steps.length > 0) {
    return (
      <>
        <div className="map-console-inspector__route">
          <span className="map-console-inspector__label">Route</span>
          <ol>
            {route.steps.map((s, i) => (
              <li key={s.exitId ?? i}>
                {s.label ?? s.toSceneId}
              </li>
            ))}
          </ol>
        </div>
        <div className="map-console-inspector__actions-row">
          {route.steps.length > 1 && onWalkRoute && (
            <Button variant="primary" size="sm" onClick={() => onWalkRoute(targetSceneId)}>
              Walk route
            </Button>
          )}
          <Button
            variant={route.steps.length > 1 ? "ghost" : "primary"}
            size="sm"
            onClick={() => go(targetSceneId)}
          >
            {route.steps.length > 1 ? "Go now" : "Go"}
          </Button>
        </div>
      </>
    );
  }

  return (
    <Button variant="primary" size="sm" onClick={() => go(targetSceneId)}>
      Go
    </Button>
  );
}

export function MapInspectorPanel({
  graph,
  worldId,
  selection,
  activeSceneId,
  onSwitchScene,
  onTravel,
  onWalkRoute,
  onKnock,
  onFitStructure,
  onFitScene,
  onViewStructure,
  onClearSelection,
  onExitHover,
  onSelectScene,
}: Props) {
  if (!graph) {
    return (
      <aside className="map-console-inspector" aria-label="Map navigation">
        <p className="map-console-inspector__empty">No map data</p>
      </aside>
    );
  }

  if (!selection) {
    return (
      <aside className="map-console-inspector" aria-label="Map navigation">
        <NavigateHome
          graph={graph}
          activeSceneId={activeSceneId}
          onTravel={onTravel}
          onKnock={onKnock}
          onExitHover={onExitHover}
          onSelectScene={onSelectScene}
        />
      </aside>
    );
  }

  if (selection.type === "scene") {
    const node = graph.nodes.find((n) => n.sceneId === selection.sceneId);
    if (!node) return null;
    const isActive = node.sceneId === activeSceneId;
    const exitFromActive = graph.edges.find(
      (e) => e.sourceSceneId === activeSceneId && e.targetSceneId === node.sceneId
    );
    const exitToActive = graph.edges.find(
      (e) => e.targetSceneId === activeSceneId && e.sourceSceneId === node.sceneId
    );

    return (
      <aside className="map-console-inspector" aria-label="Map navigation">
        <div className="map-console-inspector__head">
          <h3>{isActive ? "Current room" : "Selected room"}</h3>
          {onClearSelection && (
            <button type="button" className="map-console-inspector__clear" onClick={onClearSelection}>
              ← Back
            </button>
          )}
        </div>
        <p className="map-console-inspector__title">{node.locationName}</p>
        {node.mapZone && <p className="map-console-inspector__meta">Zone: {node.mapZone}</p>}
        {node.levelIndex != null && (
          <p className="map-console-inspector__meta">Level {node.levelIndex}</p>
        )}
        {node.presentCount > 0 && (
          <p className="map-console-inspector__meta">{node.presentCount} present</p>
        )}
        <div className="map-console-inspector__actions">
          {isActive ? (
            <p className="map-console-inspector__badge">You are in this room</p>
          ) : exitFromActive && onTravel ? (
            <>
              <p className="map-console-inspector__lead">Travel through this exit?</p>
              <Button variant="primary" size="sm" onClick={() => onTravel(node.sceneId)}>
                Go to {node.locationName}
              </Button>
              {onKnock && (
                <Button variant="ghost" size="sm" onClick={() => onKnock(node.sceneId)}>
                  Knock instead
                </Button>
              )}
            </>
          ) : worldId && (onTravel || onSwitchScene) ? (
            <>
              <p className="map-console-inspector__lead">Move your persona here?</p>
              <SceneRouteActions
                worldId={worldId}
                targetSceneId={node.sceneId}
                activeSceneId={activeSceneId}
                onTravel={onTravel}
                onWalkRoute={onWalkRoute}
                onSwitchScene={onSwitchScene}
              />
            </>
          ) : onSwitchScene ? (
            <>
              <p className="map-console-inspector__lead">Move your persona here?</p>
              <Button variant="primary" size="sm" onClick={() => onSwitchScene(node.sceneId)}>
                Go to {node.locationName}
              </Button>
            </>
          ) : null}
          {!isActive && exitToActive && onKnock && !exitFromActive && (
            <Button variant="ghost" size="sm" onClick={() => onKnock(node.sceneId)}>
              Knock
            </Button>
          )}
          {onFitScene && (
            <Button variant="ghost" size="sm" onClick={() => onFitScene(node.sceneId)}>
              Center on map
            </Button>
          )}
        </div>
      </aside>
    );
  }

  if (selection.type === "exit") {
    const edge = graph.edges.find((e) => e.exitId === selection.exitId);
    if (!edge) return null;
    const target = graph.nodes.find((n) => n.sceneId === edge.targetSceneId);
    const fromActive = edge.sourceSceneId === activeSceneId;

    return (
      <aside className="map-console-inspector" aria-label="Map navigation">
        <div className="map-console-inspector__head">
          <h3>Path selected</h3>
          {onClearSelection && (
            <button type="button" className="map-console-inspector__clear" onClick={onClearSelection}>
              ← Back
            </button>
          )}
        </div>
        <p className="map-console-inspector__title">{edge.label}</p>
        {target && (
          <p className="map-console-inspector__lead">
            Leads to <strong>{target.locationName}</strong>
          </p>
        )}
        {edge.direction && <p className="map-console-inspector__meta">Direction {edge.direction}</p>}
        {edge.travelSteps != null && edge.travelSteps > 1 && (
          <p className="map-console-inspector__meta">About {edge.travelSteps} steps away</p>
        )}
        {fromActive && onTravel && target && (
          <div className="map-console-inspector__actions">
            <Button variant="primary" size="sm" onClick={() => onTravel(target.sceneId)}>
              Go to {target.locationName}
            </Button>
            {onKnock && (
              <Button variant="ghost" size="sm" onClick={() => onKnock(target.sceneId)}>
                Knock
              </Button>
            )}
          </div>
        )}
        {!fromActive && target && (
          <p className="map-console-inspector__meta">This path does not start from your current room.</p>
        )}
      </aside>
    );
  }

  const st = graph.structures?.find((s) => s.structureId === selection.structureId);
  if (!st) return null;
  const floorNodes = graph.nodes.filter((n) => n.structureId === st.structureId);
  const levels = new Set(floorNodes.map((n) => n.levelIndex ?? 0));

  return (
    <aside className="map-console-inspector" aria-label="Map navigation">
      <div className="map-console-inspector__head">
        <h3>Building</h3>
        {onClearSelection && (
          <button type="button" className="map-console-inspector__clear" onClick={onClearSelection}>
            ← Back
          </button>
        )}
      </div>
      <p className="map-console-inspector__title">{st.displayName}</p>
      <p className="map-console-inspector__meta">
        {floorNodes.length} room(s) · {levels.size} level(s)
      </p>
      <p className="map-console-inspector__lead">Click a room below to travel or inspect.</p>
      <div className="map-console-inspector__actions">
        {onFitStructure && (
          <Button variant="ghost" size="sm" onClick={() => onFitStructure(st.structureId)}>
            Center on map
          </Button>
        )}
        {onViewStructure && (
          <Button variant="ghost" size="sm" onClick={onViewStructure}>
            Structure view
          </Button>
        )}
      </div>
      <ul className="map-console-inspector__rooms">
        {floorNodes.map((n) => {
          const exit = graph.edges.find(
            (e) => e.sourceSceneId === activeSceneId && e.targetSceneId === n.sceneId
          );
          return (
            <li key={n.sceneId}>
              <button
                type="button"
                className={n.isActive ? "map-console-inspector__room--active" : undefined}
                onClick={() => {
                  if (n.isActive) onFitScene?.(n.sceneId);
                  else if (exit && onTravel) onTravel(n.sceneId);
                  else onSwitchScene?.(n.sceneId);
                }}
                onMouseEnter={() => exit && onExitHover?.(exit.exitId)}
                onMouseLeave={() => onExitHover?.(null)}
              >
                {n.locationName}
                {n.isActive ? " (you)" : exit ? " → Go" : ""}
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
