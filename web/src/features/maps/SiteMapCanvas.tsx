import { useCallback, useMemo, useRef, useState } from "react";
import type { SpatialGraph } from "../../api/client";
import {
  activeLevel,
  activeStructureId,
  levelLabelFor,
  levelsForStructure,
  personaOffSitePlan,
  type MapViewMode,
  prepareGraphForView,
} from "./floorLevels";
import { LevelStackView } from "./LevelStackView";
import { MapRenderer } from "./MapRenderer";
import { structureEnvelope } from "./layoutGeometry";
import type { MapGraph, MapNode } from "./types";

type Props = {
  graph: SpatialGraph | null;
  onClose: () => void;
  onEnhanceLayout?: () => void;
};

const VB = 100;
const MODES: { id: MapViewMode; label: string }[] = [
  { id: "site", label: "Site" },
  { id: "structure", label: "Structure" },
  { id: "floor", label: "Floor" },
  { id: "stack", label: "Stack" },
];

function toMapGraph(graph: SpatialGraph): MapGraph {
  return graph as MapGraph;
}

export function SiteMapCanvas({ graph, onClose, onEnhanceLayout }: Props) {
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [viewMode, setViewMode] = useState<MapViewMode>("site");
  const [selectedLevel, setSelectedLevel] = useState<number | null>(null);
  const dragRef = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

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

  const fitWorld = useCallback(() => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
  }, []);

  const fitActiveStructure = useCallback(() => {
    if (!graph) return;
    const active = graph.nodes.find((n) => n.isActive);
    const sid = active?.structureId;
    if (!sid) {
      fitWorld();
      return;
    }
    const st = graph.structures?.find((s) => s.structureId === sid);
    const env = structureEnvelope(sid, graph.nodes as MapNode[], st?.boundary);
    if (!env) {
      fitWorld();
      return;
    }
    const w = env.maxX - env.minX;
    const h = env.maxY - env.minY;
    const cx = (env.minX + env.maxX) / 2;
    const cy = (env.minY + env.maxY) / 2;
    const scale = Math.min(VB / Math.max(w, 20), VB / Math.max(h, 20)) * 0.85;
    setZoom(scale);
    setPan({ x: VB / 2 - cx * scale, y: VB / 2 - cy * scale });
  }, [graph, fitWorld]);

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((z) => Math.min(4, Math.max(0.5, z * delta)));
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    dragRef.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragRef.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const scale = rect.width / VB;
    const dx = (e.clientX - dragRef.current.x) / scale;
    const dy = (e.clientY - dragRef.current.y) / scale;
    setPan({ x: dragRef.current.panX + dx, y: dragRef.current.panY + dy });
  };

  const onPointerUp = () => {
    dragRef.current = null;
  };

  const viewportRect = {
    x: -pan.x / zoom + (VB - VB / zoom) / 2,
    y: -pan.y / zoom + (VB - VB / zoom) / 2,
    w: VB / zoom,
    h: VB / zoom,
  };

  const displayGraph =
    prepared && graph
      ? ({
          ...graph,
          nodes: prepared.graph.nodes,
          edges: prepared.graph.edges,
          structures: prepared.graph.structures,
        } as SpatialGraph)
      : graph;

  return (
    <div
      className="map-overlay map-canvas map-canvas--site"
      role="dialog"
      aria-label="World map canvas"
      onKeyDown={(e) => e.key === "Escape" && onClose()}
    >
      <header className="map-overlay-header">
        <div className="map-overlay-title">
          <h2>World map</h2>
          {viewMode === "site" && (
            <p className="map-view-hint">
              {personaOffSitePlan(mg!)
                ? "Site plan shows ground floor. You are on another level — see badge or Stack view."
                : "Site plan — ground floor of each building."}
            </p>
          )}
          {viewMode === "floor" && focusStructId && (
            <p className="map-view-hint">
              {levelLabelFor(mg!.nodes, focusStructId, focusLevel)}
            </p>
          )}
          {viewMode === "stack" && (
            <p className="map-view-hint">Vertical stack — use Floor for a single level.</p>
          )}
        </div>
        <nav className="map-mode-tabs" aria-label="Map view mode">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              className={
                viewMode === m.id ? "map-mode-tabs__active" : "map-mode-tabs__btn"
              }
              aria-current={viewMode === m.id ? "page" : undefined}
              onClick={() => setViewMode(m.id)}
            >
              {m.label}
            </button>
          ))}
        </nav>
        <div className="map-overlay-actions">
          <button type="button" onClick={fitWorld}>
            Fit world
          </button>
          <button type="button" onClick={fitActiveStructure}>
            Fit structure
          </button>
          {onEnhanceLayout && (
            <button type="button" onClick={onEnhanceLayout}>
              Enhance layout
            </button>
          )}
          <button type="button" onClick={onClose}>
            Close
          </button>
        </div>
      </header>
      <div className="map-canvas-body map-canvas-body--site">
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
          className={`site-map-viewport${viewMode === "stack" ? " site-map-viewport--stack" : ""}`}
          onWheel={viewMode === "stack" ? undefined : onWheel}
          onPointerDown={viewMode === "stack" ? undefined : onPointerDown}
          onPointerMove={viewMode === "stack" ? undefined : onPointerMove}
          onPointerUp={viewMode === "stack" ? undefined : onPointerUp}
          onPointerLeave={viewMode === "stack" ? undefined : onPointerUp}
        >
          {viewMode === "stack" ? (
            <LevelStackView graph={graph} structureId={focusStructId} />
          ) : (
            <div
              className="site-map-transform"
              style={{
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                transformOrigin: "center center",
              }}
            >
              <MapRenderer
                graph={displayGraph}
                offPlanActive={prepared?.offPlanActive}
                showCompass
                showSiteUnderlay
                showScaleBar
                className="site-map-main"
                viewFit="full"
              />
            </div>
          )}
        </div>
        {viewMode !== "stack" && (
          <aside className="map-pip" aria-label="Mini-map inset">
            <MapRenderer
              graph={displayGraph}
              offPlanActive={prepared?.offPlanActive}
              viewportRect={viewportRect}
              className="map-pip-inner"
              viewFit="neighborhood"
              showZones={false}
            />
          </aside>
        )}
        {graph?.structures && graph.structures.length > 0 && (
          <aside className="map-canvas-structures">
            <h3>Structures</h3>
            <ul>
              {graph.structures.map((s) => (
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
