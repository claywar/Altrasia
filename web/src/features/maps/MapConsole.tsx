import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type NavigationRoute, type SceneMapArtifact, type SpatialGraph } from "../../api/client";
import { FocusTrap } from "../../ui/FocusTrap";
import { MapAuthorPanel } from "./MapAuthorPanel";
import { MapInspectorPanel, type MapSelection } from "./MapInspectorPanel";
import { MapLayersPanel } from "./MapLayersPanel";
import { MapRenderer } from "./MapRenderer";
import { DEFAULT_MAP_LAYERS, type MapLayerVisibility } from "./mapLayers";
import {
  activeLevel,
  activeStructureId,
  defaultViewModeForGraph,
  levelLabelFor,
  levelsForStructure,
  type MapViewMode,
  prepareGraphForView,
} from "./floorLevels";
import { LevelStackPanel } from "./LevelStackPanel";
import { destinationsFromActive, mapViewCapabilities } from "./mapNavigation";
import { MapPipChrome } from "./MapPipChrome";
import { MapViewportGuide } from "./MapViewportGuide";
import { MapViewModeSelector } from "./MapViewModeSelector";
import { useMapViewport } from "./useMapViewport";
import type { MapGraph } from "./types";

const GUIDE_STORAGE_KEY = "altrasia.mapConsole.guideDismissed";

export type MapConsoleMode = "navigate" | "author";

type Props = {
  graph: SpatialGraph | null;
  worldId: string;
  variant?: "full" | "slideOver";
  onClose: () => void;
  onEnhanceLayout?: () => void;
  onSwitchScene?: (sceneId: string) => void;
  onTravel?: (targetSceneId: string) => void;
  onWalkRoute?: (targetSceneId: string) => void | Promise<void>;
  onKnock?: (targetSceneId: string) => void;
  highlightedExitId?: string | null;
  onExitHover?: (exitId: string | null) => void;
  onGraphRefresh?: () => void;
  externalSelectedSceneId?: string | null;
  onExternalSelectScene?: (sceneId: string) => void;
  onPatchPosition?: (sceneId: string, x: number, y: number) => void;
};

const MODE_KEYS: { id: MapViewMode; key: string }[] = [
  { id: "site", key: "1" },
  { id: "structure", key: "2" },
  { id: "floor", key: "3" },
  { id: "stack", key: "4" },
];

function toMapGraph(graph: SpatialGraph): MapGraph {
  return graph as MapGraph;
}

export function MapConsole({
  graph,
  worldId,
  variant = "full",
  onClose,
  onEnhanceLayout,
  onSwitchScene,
  onTravel,
  onWalkRoute,
  onKnock,
  highlightedExitId = null,
  onExitHover,
  onGraphRefresh,
  externalSelectedSceneId = null,
  onExternalSelectScene,
  onPatchPosition,
}: Props) {
  const slideOver = variant === "slideOver";
  const [viewMode, setViewMode] = useState<MapViewMode>(() =>
    graph ? defaultViewModeForGraph(toMapGraph(graph)) : "site"
  );
  const [selectedLevel, setSelectedLevel] = useState<number | null>(null);
  const [consoleMode, setConsoleMode] = useState<MapConsoleMode>("navigate");
  const [layers, setLayers] = useState<MapLayerVisibility>(DEFAULT_MAP_LAYERS);
  const [selection, setSelection] = useState<MapSelection>(null);
  const [layersOpen, setLayersOpen] = useState(false);
  const [guideDismissed, setGuideDismissed] = useState(
    () => typeof localStorage !== "undefined" && localStorage.getItem(GUIDE_STORAGE_KEY) === "1"
  );
  const [archStyle, setArchStyle] = useState<"diagram" | "blueprint" | "minimal">(
    (graph?.layout?.architectureStyle as "diagram" | "blueprint" | "minimal") ?? "diagram"
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const viewport = useMapViewport(graph);
  const [sceneArtifacts, setSceneArtifacts] = useState<Record<string, SceneMapArtifact>>({});
  const [previewRoute, setPreviewRoute] = useState<NavigationRoute | null>(null);

  const mg = graph ? toMapGraph(graph) : null;
  const focusStructId = mg ? activeStructureId(mg) : undefined;
  const focusLevel = selectedLevel ?? (mg ? activeLevel(mg) : 0);
  const levelOptions = useMemo(
    () => (mg && focusStructId ? levelsForStructure(mg.nodes, focusStructId) : []),
    [mg, focusStructId]
  );

  const prepared = useMemo(() => {
    if (!mg) return null;
    return prepareGraphForView(mg, viewMode, { selectedLevel: focusLevel });
  }, [mg, viewMode, focusLevel]);

  const displayGraph = useMemo(() => {
    if (!prepared || !graph) return graph;
    return {
      ...graph,
      nodes: prepared.graph.nodes,
      edges: prepared.graph.edges,
      structures: prepared.graph.structures,
      layout: { ...graph.layout, architectureStyle: archStyle },
    } as SpatialGraph;
  }, [prepared, graph, archStyle]);

  const selectedSceneId =
    selection?.type === "scene" ? selection.sceneId : null;

  const routeHighlightExitId =
    previewRoute?.steps?.[0]?.exitId ?? highlightedExitId ?? null;

  useEffect(() => {
    if (!graph || !selectedSceneId || selectedSceneId === graph.activeSceneId) {
      setPreviewRoute(null);
      return;
    }
    let cancelled = false;
    api
      .navigationRoute(worldId, graph.activeSceneId, selectedSceneId)
      .then((r) => {
        if (!cancelled) setPreviewRoute(r);
      })
      .catch(() => {
        if (!cancelled) setPreviewRoute(null);
      });
    return () => {
      cancelled = true;
    };
  }, [graph, worldId, selectedSceneId]);
  const selectedExitId =
    selection?.type === "exit" ? selection.exitId : null;

  const layoutIncomplete =
    graph?.layoutStatus === "missing" ||
    graph?.layoutStatus === "partial" ||
    (!graph?.layoutStatus &&
      graph &&
      graph.nodes.length >= 2 &&
      !graph.nodes.some((n) => n.layout && (n.layout.x !== 50 || n.layout.y !== 50)));

  const activeNode = graph?.nodes.find((n) => n.isActive);
  const destinations = graph ? destinationsFromActive(graph) : [];
  const viewCaps = mapViewCapabilities(graph);
  const showViewportGuide =
    consoleMode === "navigate" && !selection && !guideDismissed && viewMode !== "stack";

  const dismissGuide = useCallback(() => {
    setGuideDismissed(true);
    try {
      localStorage.setItem(GUIDE_STORAGE_KEY, "1");
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (graph?.layout?.architectureStyle) {
      setArchStyle(
        graph.layout.architectureStyle as "diagram" | "blueprint" | "minimal"
      );
    }
  }, [graph?.layout?.architectureStyle]);

  const activeSceneId = graph?.activeSceneId;

  useEffect(() => {
    if (!graph || viewMode === "stack") {
      setSceneArtifacts({});
      return;
    }
    const sceneIds = prepared?.graph.nodes.map((n) => n.sceneId) ?? [];
    if (!sceneIds.length) {
      setSceneArtifacts({});
      return;
    }
    let cancelled = false;
    Promise.all(
      sceneIds.map(async (sceneId) => {
        try {
          const res = await api.getSceneMapArtifact(worldId, sceneId);
          return [sceneId, res.artifact] as const;
        } catch {
          return [sceneId, null] as const;
        }
      })
    ).then((pairs) => {
      if (cancelled) return;
      const next: Record<string, SceneMapArtifact> = {};
      for (const [id, art] of pairs) {
        if (art) next[id] = art;
      }
      setSceneArtifacts(next);
    });
    return () => {
      cancelled = true;
    };
  }, [graph, worldId, viewMode, prepared?.graph.nodes]);

  useEffect(() => {
    if (!graph) return;
    const mgLocal = toMapGraph(graph);
    setViewMode(defaultViewModeForGraph(mgLocal));
    setSelectedLevel(activeLevel(mgLocal));
    const structId = activeStructureId(mgLocal);
    if (structId) viewport.fitStructure(structId);
    else viewport.fitWorld();
  }, [activeSceneId]); // eslint-disable-line react-hooks/exhaustive-deps -- refit when persona moves

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable) {
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        if (showViewportGuide) {
          dismissGuide();
          return;
        }
        if (selection) setSelection(null);
        else onClose();
        return;
      }
      if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        if (selection?.type === "scene") viewport.fitScene(selection.sceneId);
        else if (selection?.type === "structure") viewport.fitStructure(selection.structureId);
        else viewport.fitActiveStructure();
        return;
      }
      if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        viewport.zoomIn();
        return;
      }
      if (e.key === "-") {
        e.preventDefault();
        viewport.zoomOut();
        return;
      }
      const mode = MODE_KEYS.find((m) => m.key === e.key);
      if (mode) {
        e.preventDefault();
        setViewMode(mode.id);
      }
      if (viewMode !== "stack") {
        const step = 4;
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          viewport.panByKeys(step, 0);
        }
        if (e.key === "ArrowRight") {
          e.preventDefault();
          viewport.panByKeys(-step, 0);
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          viewport.panByKeys(0, step);
        }
        if (e.key === "ArrowDown") {
          e.preventDefault();
          viewport.panByKeys(0, -step);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selection, viewMode, viewport, onClose, showViewportGuide, dismissGuide]);

  const handleNodeSelect = useCallback(
    (sceneId: string) => {
      setSelection({ type: "scene", sceneId });
      onExternalSelectScene?.(sceneId);
    },
    [onExternalSelectScene]
  );

  useEffect(() => {
    if (slideOver && externalSelectedSceneId) {
      setSelection({ type: "scene", sceneId: externalSelectedSceneId });
    }
  }, [slideOver, externalSelectedSceneId]);

  const handleEdgeSelect = useCallback((exitId: string) => {
    setSelection({ type: "exit", exitId });
  }, []);

  const handleStructureSelect = useCallback((structureId: string) => {
    setSelection({ type: "structure", structureId });
    viewport.fitStructure(structureId);
  }, [viewport]);

  const handleTravelVertical = useCallback(
    (exitId: string) => {
      const edge = graph?.edges.find((e) => e.exitId === exitId);
      if (edge?.targetSceneId && onTravel) onTravel(edge.targetSceneId);
    },
    [graph?.edges, onTravel]
  );

  if (slideOver && graph) {
    return (
      <div className="map-console map-console--slide-over" data-testid="map-console-slide">
        <div className="map-console-body map-console-body--slide-only">
          <div className="map-console-center map-console-center--full">
            <div
              ref={containerRef}
              className="map-console-viewport"
              tabIndex={0}
              onWheel={viewport.onWheel}
              onPointerDown={viewport.onPointerDown}
              onPointerMove={(e) => viewport.onPointerMove(e, containerRef.current)}
              onPointerUp={viewport.onPointerUp}
              onPointerLeave={viewport.onPointerUp}
            >
              <div
                className="site-map-transform"
                style={{
                  transform: `translate(${viewport.pan.x}px, ${viewport.pan.y}px) scale(${viewport.zoom})`,
                  transformOrigin: "center center",
                }}
              >
                <MapRenderer
                  graph={displayGraph}
                  offPlanActive={prepared?.offPlanActive}
                  className="site-map-main"
                  viewFit="full"
                  interactive
                  showEnvelopes
                  showEdges
                  showLabels
                  architectureStyle={archStyle}
                  worldMap={graph.worldMap}
                  highlightedExitId={routeHighlightExitId}
                  selectedSceneId={selectedSceneId}
                  onNodeSelect={handleNodeSelect}
                  onEdgeHover={onExitHover}
                  onNodePositionChange={
                    onPatchPosition
                      ? (sceneId, pos) => onPatchPosition(sceneId, pos.x, pos.y)
                      : undefined
                  }
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="map-console-scrim"
      role="presentation"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <FocusTrap>
        <div
          className="map-console"
          role="dialog"
          aria-label="World map console"
          data-testid="map-console"
          onClick={(e) => e.stopPropagation()}
        >
          <header className="map-console-header">
            <div className="map-console-header__title">
              <h2>World map</h2>
              {activeNode && (
                <p className="map-console-breadcrumb">
                  {activeNode.locationName}
                  {activeNode.mapZone ? ` · ${activeNode.mapZone}` : ""}
                </p>
              )}
            </div>
            <MapViewModeSelector
              graph={graph}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              caps={viewCaps}
            />
            <div className="map-console-header__modes">
              <div className="map-console-mode-toggle" role="group" aria-label="Console mode">
                <button
                  type="button"
                  className={consoleMode === "navigate" ? "map-console-mode-toggle__active" : undefined}
                  onClick={() => setConsoleMode("navigate")}
                >
                  Navigate
                </button>
                <button
                  type="button"
                  className={consoleMode === "author" ? "map-console-mode-toggle__active" : undefined}
                  onClick={() => setConsoleMode("author")}
                >
                  Author
                </button>
              </div>
            </div>
            <div className="map-console-header__actions">
              <button type="button" onClick={viewport.fitWorld} title="Fit world (F)">
                Fit world
              </button>
              <button
                type="button"
                onClick={viewport.fitActiveStructure}
                title="Fit active structure"
              >
                Fit structure
              </button>
              <button
                type="button"
                className="map-console-zoom-btn"
                onClick={viewport.zoomOut}
                aria-label="Zoom out"
              >
                −
              </button>
              <span className="map-console-zoom-label" aria-live="polite">
                {viewport.zoomPercent}%
              </span>
              <button
                type="button"
                className="map-console-zoom-btn"
                onClick={viewport.zoomIn}
                aria-label="Zoom in"
              >
                +
              </button>
              {layoutIncomplete && onEnhanceLayout && (
                <button type="button" onClick={onEnhanceLayout}>
                  Enhance layout
                </button>
              )}
              <button type="button" onClick={onClose}>
                Close
              </button>
            </div>
          </header>

          {consoleMode === "navigate" && activeNode && destinations.length > 0 && (
            <p className="map-console-hint map-console-hint--action">
              {destinations.length} exit{destinations.length === 1 ? "" : "s"} from{" "}
              {activeNode.locationName} — use <strong>Go somewhere</strong> on the right.
            </p>
          )}

          <div className="map-console-body">
            <MapLayersPanel
              layers={layers}
              onChange={setLayers}
              architectureStyle={archStyle}
              onArchitectureStyle={setArchStyle}
              collapsed={!layersOpen}
              onToggleCollapsed={() => setLayersOpen((v) => !v)}
            />

            <div className="map-console-center">
              {levelOptions.length > 1 &&
                (viewMode === "floor" || viewMode === "structure") &&
                focusStructId && (
                  <aside className="map-level-selector" aria-label="Floor selector">
                    <h3>Floors</h3>
                    <ul>
                      {levelOptions.map((lvl) => (
                        <li key={lvl}>
                          <button
                            type="button"
                            className={
                              focusLevel === lvl ? "map-level-selector__active" : undefined
                            }
                            onClick={() => setSelectedLevel(lvl)}
                          >
                            {levelLabelFor(mg!.nodes, focusStructId, lvl)}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </aside>
                )}

              <div
                ref={containerRef}
                className={`map-console-viewport${viewMode === "stack" ? " map-console-viewport--stack" : ""}`}
                tabIndex={0}
                aria-label="Map viewport. Drag to pan; scroll to zoom; arrow keys pan when focused."
                onWheel={viewMode === "stack" ? undefined : viewport.onWheel}
                onPointerDown={viewMode === "stack" ? undefined : viewport.onPointerDown}
                onPointerMove={
                  viewMode === "stack"
                    ? undefined
                    : (e) => viewport.onPointerMove(e, containerRef.current)
                }
                onPointerUp={viewMode === "stack" ? undefined : viewport.onPointerUp}
                onPointerLeave={viewMode === "stack" ? undefined : viewport.onPointerUp}
                onTouchStart={viewMode === "stack" ? undefined : viewport.onTouchStart}
                onTouchMove={viewMode === "stack" ? undefined : viewport.onTouchMove}
              >
                {viewMode === "stack" ? (
                  <LevelStackPanel
                    graph={graph}
                    structureId={focusStructId}
                    focusLevel={focusLevel}
                    onFocusLevel={(lvl) => setSelectedLevel(lvl)}
                    selectedSceneId={selectedSceneId}
                    onSelectScene={handleNodeSelect}
                    onTravelScene={onTravel}
                    onTravelVertical={handleTravelVertical}
                  />
                ) : (
                  <div
                    className="site-map-transform"
                    style={{
                      transform: `translate(${viewport.pan.x}px, ${viewport.pan.y}px) scale(${viewport.zoom})`,
                      transformOrigin: "center center",
                    }}
                  >
                    <MapRenderer
                      graph={displayGraph}
                      offPlanActive={prepared?.offPlanActive}
                      showCompass={layers.compass}
                      showSiteUnderlay={layers.underlay}
                      showScaleBar={layers.scaleBar}
                      showZones={layers.zones}
                      showEnvelopes={layers.structures}
                      showEdges={layers.edges}
                      showLabels={layers.labels}
                      showZoneBands={layers.zoneBands}
                      fogInactiveStructures={layers.fog}
                      className="site-map-main"
                      viewFit="full"
                      interactive={consoleMode === "navigate"}
                      architectureStyle={archStyle}
                      worldMap={graph?.worldMap}
                      highlightedExitId={routeHighlightExitId}
                      selectedSceneId={selectedSceneId}
                      selectedExitId={selectedExitId}
                      onNodeSelect={handleNodeSelect}
                      onEdgeSelect={handleEdgeSelect}
                      onEdgeHover={onExitHover}
                      onStructureSelect={handleStructureSelect}
                      sceneArtifacts={sceneArtifacts}
                      onArtifactTravel={onTravel}
                    />
                  </div>
                )}
              </div>

              {showViewportGuide && activeNode && (
                <MapViewportGuide
                  locationName={activeNode.locationName}
                  destinationCount={destinations.length}
                  onDismiss={dismissGuide}
                />
              )}

              {viewMode !== "stack" && (
                <aside className="map-pip map-console-pip" aria-label="Overview inset">
                  <MapPipChrome
                    viewMode={viewMode}
                    caps={viewCaps}
                    onSwitchView={setViewMode}
                  />
                  <MapRenderer
                    graph={displayGraph}
                    offPlanActive={prepared?.offPlanActive}
                    viewportRect={viewport.viewportRect}
                    className="map-pip-inner"
                    viewFit="neighborhood"
                    showZones={false}
                    architectureStyle={archStyle}
                    worldMap={graph?.worldMap}
                  />
                </aside>
              )}

              {graph?.structures && graph.structures.length > 0 && (
                <aside className="map-canvas-structures map-console-structures" aria-label="Structures">
                  <h3>Structures</h3>
                  <ul>
                    {graph.structures.map((s) => (
                      <li key={s.structureId}>
                        <button
                          type="button"
                          className={
                            selection?.type === "structure" &&
                            selection.structureId === s.structureId
                              ? "map-console-structures__active"
                              : undefined
                          }
                          onClick={() => handleStructureSelect(s.structureId)}
                        >
                          {s.displayName}
                          {s.containsActiveScene ? " (active)" : ""}
                        </button>
                      </li>
                    ))}
                  </ul>
                </aside>
              )}
            </div>

            {consoleMode === "navigate" ? (
              <MapInspectorPanel
                graph={graph}
                worldId={worldId}
                selection={selection}
                activeSceneId={graph?.activeSceneId ?? ""}
                onSwitchScene={onSwitchScene}
                onTravel={onTravel}
                onWalkRoute={onWalkRoute}
                onKnock={onKnock}
                onFitStructure={viewport.fitStructure}
                onFitScene={viewport.fitScene}
                onViewStructure={() => setViewMode("structure")}
                onClearSelection={() => setSelection(null)}
                onExitHover={onExitHover}
                onSelectScene={(sceneId) => setSelection({ type: "scene", sceneId })}
              />
            ) : (
              <MapAuthorPanel
                worldId={worldId}
                graph={graph}
                onCommitted={() => {
                  onGraphRefresh?.();
                  setConsoleMode("navigate");
                }}
              />
            )}
          </div>

          <footer className="map-console-status" aria-label="Map status">
            <span>Mode: {consoleMode === "navigate" ? "Navigate" : "Author"}</span>
            <span>View: {viewMode}</span>
            {viewport.cursorMap && (
              <span>
                Cursor {viewport.cursorMap.x}, {viewport.cursorMap.y}
              </span>
            )}
            <span className="map-console-status__shortcuts">
              Right panel: travel · Esc close · M toggle map
            </span>
          </footer>
        </div>
      </FocusTrap>
    </div>
  );
}
