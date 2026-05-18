import { useMemo, useRef, useState } from "react";
import type { SpatialGraph } from "../../api/client";
import { MapCompass } from "./MapChrome";
import { computeViewBox, filterGraphForView, type ViewFitMode } from "./computeViewBox";
import { arrowMarkerId, routeEdge } from "./edgeRouting";
import {
  computeNeighborhoodDim,
  edgeEndpoints,
  hasDirectionalEdges,
  hubEdgeIndex,
  nodeFootprint,
  structureEnvelope,
  zoneBandsFromNodes,
} from "./layoutGeometry";
import { MapNodeShape } from "./mapShapes";
import type { MapEdge, MapGraph, Point } from "./types";

export type MapRendererProps = {
  graph: SpatialGraph | null;
  highlightedExitId?: string | null;
  className?: string;
  showCompass?: boolean;
  showZones?: boolean;
  showEnvelopes?: boolean;
  viewportRect?: { x: number; y: number; w: number; h: number };
  viewFit?: ViewFitMode;
  enablePan?: boolean;
};

function toMapGraph(graph: SpatialGraph): MapGraph {
  return graph as MapGraph;
}

function truncateLabel(name: string, max = 14): string {
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

export function MapRenderer({
  graph,
  highlightedExitId,
  className = "",
  showCompass = true,
  showZones = true,
  showEnvelopes = true,
  viewportRect,
  viewFit = "neighborhood",
  enablePan = false,
}: MapRendererProps) {
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const mg = useMemo(() => (graph ? filterGraphForView(toMapGraph(graph), viewFit) : null), [graph, viewFit]);
  const viewBox = useMemo(() => (mg ? computeViewBox(mg, viewFit) : { x: 0, y: 0, w: 100, h: 100 }), [mg, viewFit]);

  if (!graph || !mg) return <div className={`minimap ${className}`}>No map</div>;

  const nodes = mg.nodes;
  const edges = mg.edges as MapEdge[];
  const dimmed = computeNeighborhoodDim(toMapGraph(graph));
  const showRose = showCompass && hasDirectionalEdges(edges);
  const nodeById = new Map(nodes.map((n) => [n.sceneId, n]));
  const footprints = nodes.map((n) => nodeFootprint(n));
  const usedBadgeSlots: Point[] = [];

  const vb = `${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`;
  const panTransform = enablePan && (pan.x !== 0 || pan.y !== 0) ? `translate(${pan.x}, ${pan.y})` : undefined;

  const onPointerDown = (e: React.PointerEvent) => {
    if (!enablePan || e.button !== 0) return;
    dragRef.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragRef.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const scale = viewBox.w / rect.width;
    setPan({
      x: dragRef.current.panX + (e.clientX - dragRef.current.x) * scale,
      y: dragRef.current.panY + (e.clientY - dragRef.current.y) * scale,
    });
  };

  const onPointerUp = () => {
    dragRef.current = null;
  };

  const placeBadge = (p: Point): Point => {
    for (const u of usedBadgeSlots) {
      if (Math.hypot(u.x - p.x, u.y - p.y) < 3.5) {
        return { x: p.x + 2.5, y: p.y - 2 };
      }
    }
    usedBadgeSlots.push(p);
    return p;
  };

  return (
    <div
      ref={containerRef}
      className={`minimap ${enablePan ? "minimap--pannable" : ""} ${className}`.trim()}
      onPointerDown={enablePan ? onPointerDown : undefined}
      onPointerMove={enablePan ? onPointerMove : undefined}
      onPointerUp={enablePan ? onPointerUp : undefined}
      onPointerLeave={enablePan ? onPointerUp : undefined}
    >
      <svg viewBox={vb} role="img" aria-label="Spatial mini-map">
        <defs>
          <marker id="map-arrow" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
            <polygon points="0,0 4,2 0,4" fill="var(--border)" />
          </marker>
          <marker id="map-arrow-hi" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
            <polygon points="0,0 4,2 0,4" fill="var(--active-scene)" />
          </marker>
          <filter id="map-active-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="0.8" floodColor="var(--accent)" floodOpacity="0.5" />
          </filter>
        </defs>

        <g transform={panTransform}>
          {/* 1. Structure fills */}
          {showEnvelopes &&
            (mg.structures ?? []).map((st) => {
              const env = structureEnvelope(st.structureId, nodes, st.boundary);
              if (!env) return null;
              const { minX, minY, maxX, maxY, vertices } = env;
              const isOutdoor = st.kind === "outdoor";
              const fill = isOutdoor ? "var(--map-outdoor-fill, rgba(255,255,255,0.04))" : "var(--map-structure-fill, rgba(120,130,150,0.12))";
              if (vertices && vertices.length >= 3) {
                return (
                  <polygon
                    key={`fill-${st.structureId}`}
                    points={vertices.map((v) => `${v.x},${v.y}`).join(" ")}
                    fill={fill}
                    stroke="none"
                  />
                );
              }
              return (
                <rect
                  key={`fill-${st.structureId}`}
                  x={minX}
                  y={minY}
                  width={maxX - minX}
                  height={maxY - minY}
                  fill={fill}
                  rx={1}
                />
              );
            })}

          {/* 2. Zone bands */}
          {showZones &&
            zoneBandsFromNodes(nodes).map((band) => (
              <g key={band.key} className="map-zone">
                <rect
                  x={band.minX}
                  y={band.bandY - 1.5}
                  width={band.maxX - band.minX}
                  height={3}
                  className="map-zone-band"
                  rx={0.5}
                />
                <text
                  x={(band.minX + band.maxX) / 2}
                  y={band.bandY}
                  textAnchor="middle"
                  fontSize={2}
                  className="map-zone-label"
                >
                  {band.mapZone}
                </text>
              </g>
            ))}

          {/* 3. Edges */}
          {edges.map((e) => {
            const a = nodeById.get(e.sourceSceneId);
            const b = nodeById.get(e.targetSceneId);
            if (!a?.layout || !b?.layout) return null;
            const { start, end } = edgeEndpoints(a, b, e);
            const obstacles = footprints.filter(
              (fp) => fp.sceneId !== a.sceneId && fp.sceneId !== b.sceneId
            );
            const { index, total } = hubEdgeIndex(edges, e.exitId);
            const offset = total > 1 ? (index - (total - 1) / 2) * 1.8 : 0;
            const routed = routeEdge(start, end, obstacles, offset);
            const highlighted = highlightedExitId === e.exitId;
            const steps = e.travelSteps ?? 1;
            const badgePos = steps > 1 ? placeBadge(routed.labelPoint) : null;
            return (
              <g key={e.exitId} className={`map-edge${highlighted ? " map-edge--hi" : ""}`}>
                <path
                  d={routed.pathD}
                  fill="none"
                  stroke={highlighted ? "var(--active-scene)" : "var(--border)"}
                  strokeWidth={highlighted ? 1.4 : steps > 1 ? 1 : 0.75}
                  strokeDasharray={steps > 1 && !highlighted ? "2 1" : undefined}
                  markerEnd={e.direction ? `url(#${arrowMarkerId(highlighted)})` : undefined}
                />
                {badgePos && (
                  <g className="map-edge-badge">
                    <rect
                      x={badgePos.x - 1.8}
                      y={badgePos.y - 1.6}
                      width={3.6}
                      height={3.2}
                      rx={0.8}
                    />
                    <text x={badgePos.x} y={badgePos.y + 0.6} textAnchor="middle" fontSize={2.2}>
                      {steps}
                    </text>
                  </g>
                )}
                {e.doorState && e.doorState !== "open" && (
                  <text
                    x={routed.doorPoint.x}
                    y={routed.doorPoint.y}
                    fontSize={2}
                    className="map-door-glyph"
                    textAnchor="middle"
                  >
                    ║
                  </text>
                )}
                <title>{e.label}</title>
              </g>
            );
          })}

          {/* 4. Envelope strokes + structure titles */}
          {showEnvelopes &&
            (mg.structures ?? []).map((st) => {
              const env = structureEnvelope(st.structureId, nodes, st.boundary);
              if (!env) return null;
              const { minX, minY, maxX, maxY, vertices } = env;
              const titleY = minY + 2.8;
              const title = truncateLabel(st.displayName);
              const titleW = title.length * 1.35 + 2;
              const titleX = (minX + maxX) / 2;
              return (
                <g key={`env-${st.structureId}`} className="map-envelope">
                  {vertices && vertices.length >= 3 ? (
                    <polygon
                      points={vertices.map((v) => `${v.x},${v.y}`).join(" ")}
                      fill="none"
                      stroke="var(--structure-stroke, var(--border))"
                      strokeWidth={0.7}
                      strokeDasharray="3 1.5"
                    />
                  ) : (
                    <rect
                      x={minX}
                      y={minY}
                      width={maxX - minX}
                      height={maxY - minY}
                      fill="none"
                      stroke="var(--structure-stroke, var(--border))"
                      strokeWidth={0.7}
                      strokeDasharray="3 1.5"
                      rx={1}
                    />
                  )}
                  <rect
                    x={titleX - titleW / 2}
                    y={minY + 0.5}
                    width={titleW}
                    height={3.2}
                    className="map-structure-title-bg"
                    rx={0.5}
                  />
                  <text
                    x={titleX}
                    y={titleY}
                    textAnchor="middle"
                    fontSize={2.2}
                    className="map-structure-label"
                  >
                    <title>{st.displayName}</title>
                    {title}
                  </text>
                </g>
              );
            })}

          {/* 5. Nodes */}
          {nodes.map((n) => {
            const fp = nodeFootprint(n);
            const isDimmed = dimmed.get(n.sceneId);
            const active = n.isActive;
            return (
              <g key={n.sceneId} filter={active ? "url(#map-active-glow)" : undefined}>
                <MapNodeShape fp={fp} active={active} dimmed={isDimmed} label={n.locationName} />
                <title>{n.locationName}</title>
              </g>
            );
          })}

          {viewportRect && (
            <rect
              x={viewportRect.x}
              y={viewportRect.y}
              width={viewportRect.w}
              height={viewportRect.h}
              fill="none"
              stroke="var(--accent)"
              strokeWidth={0.6}
              strokeDasharray="1 0.5"
              className="map-viewport-rect"
            />
          )}

          {showRose && <MapCompass x={viewBox.x + viewBox.w - 8} y={viewBox.y + 6} />}
        </g>
      </svg>
    </div>
  );
}
