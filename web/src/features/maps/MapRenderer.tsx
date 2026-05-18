import { useMemo, useRef, useState } from "react";
import type { SpatialGraph } from "../../api/client";
import { MapCompass, MapScaleBar } from "./MapChrome";
import { computeViewBox, filterGraphForView, type ViewFitMode } from "./computeViewBox";
import { computeCorridors } from "./corridorGeometry";
import { arrowMarkerId, routeEdge } from "./edgeRouting";
import {
  computeNeighborhoodDim,
  edgeEndpoints,
  hasDirectionalEdges,
  hubEdgeIndex,
  nodeFootprint,
  zoneBandsFromNodes,
} from "./layoutGeometry";
import {
  levelBadgeShort,
  structureFloorCountLabel,
  structureLabels,
  zoneBadgesFromNodes,
} from "./labelLayout";
import { CorridorShape, MapNodeShape } from "./mapShapes";
import { envelopeDashForKind, resolveArchitectureStyle, styleTokens } from "./mapStyle";
import { DoorGlyph, GateGlyph, pathAngleAtPoint } from "./pathGlyphs";
import { SiteUnderlay } from "./SiteUnderlay";
import { getEnvelopePath, SmoothEnvelope } from "./SmoothEnvelope";
import type { MapEdge, MapGraph, MapNode, MapStructure, Point } from "./types";

export type MapRendererProps = {
  graph: SpatialGraph | null;
  highlightedExitId?: string | null;
  className?: string;
  showCompass?: boolean;
  showZones?: boolean;
  showEnvelopes?: boolean;
  showSiteUnderlay?: boolean;
  showScaleBar?: boolean;
  viewportRect?: { x: number; y: number; w: number; h: number };
  viewFit?: ViewFitMode;
  enablePan?: boolean;
  architectureStyle?: "diagram" | "blueprint" | "minimal";
  /** Persona on another floor — mark structure shell, do not draw that room on plan. */
  offPlanActive?: MapNode;
  showZoneBands?: boolean;
};

function toMapGraph(graph: SpatialGraph): MapGraph {
  return graph as MapGraph;
}

export function MapRenderer({
  graph,
  highlightedExitId,
  className = "",
  showCompass = true,
  showZones = true,
  showEnvelopes = true,
  showSiteUnderlay = false,
  showScaleBar = false,
  viewportRect,
  viewFit = "neighborhood",
  enablePan = false,
  architectureStyle: styleProp,
  offPlanActive,
  showZoneBands = true,
}: MapRendererProps) {
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const mg = useMemo(() => (graph ? filterGraphForView(toMapGraph(graph), viewFit) : null), [graph, viewFit]);
  const viewBox = useMemo(() => (mg ? computeViewBox(mg, viewFit) : { x: 0, y: 0, w: 100, h: 100 }), [mg, viewFit]);

  const archStyle = styleProp ?? resolveArchitectureStyle(graph);
  const activeStructId = graph?.nodes.find((n) => n.isActive)?.structureId;
  const tokens = styleTokens(archStyle, Boolean(activeStructId));

  const corridors = useMemo(
    () => (mg ? computeCorridors(mg.nodes, mg.edges as MapEdge[]) : []),
    [mg]
  );

  const structLabels = useMemo(
    () => (mg && showEnvelopes ? structureLabels(mg.structures ?? [], mg.nodes) : []),
    [mg, showEnvelopes]
  );

  const zoneBadges = useMemo(
    () => (mg && showZones ? zoneBadgesFromNodes(mg.structures ?? [], mg.nodes) : []),
    [mg, showZones]
  );

  const zoneBands = useMemo(
    () => (mg && showZoneBands ? zoneBandsFromNodes(mg.nodes) : []),
    [mg, showZoneBands]
  );

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

  const structureFill = (st: MapStructure) => {
    if (!tokens.showStructureFill) return "none";
    if (st.containsActiveScene || st.structureId === activeStructId) {
      return tokens.structureFillActive;
    }
    return tokens.structureFillOther;
  };

  return (
    <div
      ref={containerRef}
      className={`minimap ${enablePan ? "minimap--pannable" : ""} map-style--${archStyle} ${className}`.trim()}
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

        {showSiteUnderlay && <SiteUnderlay viewBox={viewBox} idPrefix="map-site" />}

        <g transform={panTransform}>
          {/* 0. Zone bands (floor / ward rails) */}
          {zoneBands.map((band) => (
            <g key={`band-${band.key}`} className="map-zone-band-group">
              <rect
                x={band.minX}
                y={band.bandY - 2}
                width={band.maxX - band.minX}
                height={3.5}
                rx={0.8}
                className="map-zone-band"
              />
              <text
                x={band.minX + 1.5}
                y={band.bandY}
                fontSize={1.6}
                className="map-zone-label"
                fontFamily={tokens.labelFont}
              >
                {band.mapZone}
              </text>
            </g>
          ))}

          {/* 1. Structure fills (smooth shells) */}
          {showEnvelopes &&
            (mg.structures ?? []).map((st) => {
              if (!tokens.showStructureFill) return null;
              const fill = structureFill(st);
              return (
                <SmoothEnvelope
                  key={`fill-${st.structureId}`}
                  structureId={st.structureId}
                  nodes={nodes}
                  boundary={st.boundary}
                  fill={fill}
                  stroke="none"
                  doubleWall={false}
                />
              );
            })}

          {/* 2. Corridor segments (interior) */}
          {corridors.map((c) => (
            <CorridorShape key={c.id} x={c.x} y={c.y} w={c.w} h={c.h} tokens={tokens} />
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
            const interiorOnly =
              Boolean(a.structureId) && a.structureId === b.structureId && !e.crossesStructure;
            const routed = routeEdge(start, end, obstacles, offset, {
              corridors,
              crossesStructure: e.crossesStructure,
              interiorOnly,
            });
            const highlighted = highlightedExitId === e.exitId;
            const steps = e.travelSteps ?? 1;
            const badgePos = steps >= 3 ? placeBadge(routed.labelPoint) : null;
            const showDoor =
              e.doorState && e.doorState !== "open" && !e.crossesStructure;
            const showGate = e.crossesStructure;
            const pathIdx = Math.min(1, routed.points.length - 2);
            const angle = pathAngleAtPoint(routed.points, pathIdx);

            return (
              <g key={e.exitId} className={`map-edge${highlighted ? " map-edge--hi" : ""}`}>
                <path
                  d={routed.pathD}
                  fill="none"
                  stroke={highlighted ? "var(--active-scene)" : "var(--map-path, var(--border))"}
                  strokeWidth={highlighted ? 1.2 : routed.outdoor ? 0.7 : 0.55}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  markerEnd={
                    !routed.outdoor && e.direction && steps <= 1
                      ? `url(#${arrowMarkerId(highlighted)})`
                      : undefined
                  }
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
                {showDoor && (
                  <DoorGlyph point={routed.doorPoint} angleDeg={angle} highlighted={highlighted} />
                )}
                {showGate && (
                  <GateGlyph
                    point={routed.labelPoint}
                    angleDeg={angle + 90}
                    highlighted={highlighted}
                  />
                )}
                <title>{e.label}</title>
              </g>
            );
          })}

          {/* 4. Envelope strokes */}
          {showEnvelopes &&
            (mg.structures ?? []).map((st) => {
              const dash = envelopeDashForKind(archStyle, st.kind) ?? tokens.envelopeDasharray;
              return (
                <SmoothEnvelope
                  key={`env-${st.structureId}`}
                  structureId={st.structureId}
                  nodes={nodes}
                  boundary={st.boundary}
                  stroke={tokens.envelopeStroke}
                  strokeWidth={tokens.envelopeStrokeWidth}
                  dasharray={dash}
                  doubleWall={tokens.doubleWall}
                />
              );
            })}

          {/* 5. Zone badges (corner) */}
          {zoneBadges.map((badge) => {
            const labelW = badge.text.length * 1.15 + 2;
            const rectX = badge.anchor === "end" ? badge.x - labelW : badge.x;
            return (
              <g key={`zone-${badge.structureId}`} className="map-zone-badge">
                <rect
                  x={rectX}
                  y={badge.y - 2.8}
                  width={labelW}
                  height={3}
                  rx={0.6}
                  className="map-zone-badge-bg"
                />
                <text
                  x={badge.anchor === "end" ? badge.x - 1 : badge.x + 1}
                  y={badge.y}
                  textAnchor={badge.anchor}
                  fontSize={1.7}
                  className="map-zone-label"
                  fontFamily={tokens.labelFont}
                >
                  {badge.text}
                </text>
              </g>
            );
          })}

          {/* 6. Structure titles (above envelope) */}
          {structLabels.map((lab) => (
            <g key={`title-${lab.structureId}`} className="map-structure-title">
              <text
                x={lab.x}
                y={lab.y}
                textAnchor="middle"
                fontSize={2.4}
                className="map-structure-label"
                fontFamily={tokens.labelFont}
              >
                <title>{lab.fullName}</title>
                {lab.text}
              </text>
            </g>
          ))}

          {/* 7. Level badges (ground on site; persona floor when upstairs) */}
          {showZones &&
            (mg.structures ?? []).map((st) => {
              const env = getEnvelopePath(st.structureId, graph.nodes as MapNode[], st.boundary);
              if (!env) return null;
              const allNodes = graph.nodes as MapNode[];
              const floorCount = structureFloorCountLabel(st.structureId, allNodes);
              const personaHere =
                offPlanActive?.structureId === st.structureId ? offPlanActive : null;
              const onPlan = mg.nodes.find((n) => n.structureId === st.structureId && n.isActive);
              let label: string | null = null;
              if (personaHere) {
                const short =
                  levelBadgeShort(personaHere.levelLabel ?? personaHere.mapZone) ??
                  personaHere.locationName;
                label = `▲ ${short}`;
              } else if (onPlan) {
                label = levelBadgeShort(onPlan.mapZone) ?? "Ground";
              } else if (floorCount) {
                label = floorCount;
              }
              if (!label) return null;
              return (
                <g key={`lvl-${st.structureId}`} className="map-level-badge">
                  <rect
                    x={env.maxX - label.length * 1.15 - 3}
                    y={env.maxY - 3.5}
                    width={label.length * 1.15 + 2}
                    height={3}
                    rx={0.4}
                    className="map-level-badge-bg"
                  />
                  <text
                    x={env.maxX - 2}
                    y={env.maxY - 1.2}
                    textAnchor="end"
                    fontSize={1.7}
                    className="map-level-badge-text"
                    fontFamily={tokens.labelFont}
                  >
                    {label}
                  </text>
                </g>
              );
            })}

          {/* 8. Persona on another floor — pin on structure shell (site plan) */}
          {offPlanActive?.structureId && (() => {
            const st = mg.structures?.find((s) => s.structureId === offPlanActive.structureId);
            const env = getEnvelopePath(
              offPlanActive.structureId,
              graph.nodes as MapNode[],
              st?.boundary
            );
            if (!env) return null;
            const cx = (env.minX + env.maxX) / 2;
            const cy = (env.minY + env.maxY) / 2;
            return (
              <g className="map-off-plan-pin" aria-label={`You are in ${offPlanActive.locationName}`}>
                <circle cx={cx} cy={cy} r={1.8} className="map-off-plan-pin__dot" />
                <circle
                  cx={cx}
                  cy={cy}
                  r={2.8}
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth={0.45}
                  opacity={0.7}
                />
              </g>
            );
          })()}

          {/* 9. Nodes */}
          {nodes.map((n) => {
            const fp = nodeFootprint(n);
            const isDimmed = dimmed.get(n.sceneId);
            const active = n.isActive;
            return (
              <g key={n.sceneId} filter={active ? "url(#map-active-glow)" : undefined}>
                <MapNodeShape
                  fp={fp}
                  active={active}
                  dimmed={isDimmed}
                  label={n.locationName}
                  tokens={tokens}
                />
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
          {showScaleBar && (
            <MapScaleBar x={viewBox.x + 4} y={viewBox.y + viewBox.h - 5} />
          )}
        </g>
      </svg>
    </div>
  );
}
