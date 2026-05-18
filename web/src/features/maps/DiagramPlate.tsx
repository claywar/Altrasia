/**
 * Single-floor diagram slice — same definition-driven geometry as MapRenderer,
 * without chrome (compass, pan, underlay). Used for stack plates and previews.
 */
import { useMemo } from "react";
import { computeCorridors } from "./corridorGeometry";
import { routeEdge } from "./edgeRouting";
import { edgeEndpoints, hubEdgeIndex, nodeFootprint } from "./layoutGeometry";
import { CorridorShape, MapNodeShape } from "./mapShapes";
import type { MapStyleTokens } from "./mapStyle";
import { SmoothEnvelope } from "./SmoothEnvelope";
import { footprintBounds } from "./layoutGeometry";
import type { MapEdge, MapNode, MapStructure } from "./types";

type Props = {
  nodes: MapNode[];
  edges: MapEdge[];
  structure?: MapStructure;
  tokens: MapStyleTokens;
  /** Ghost inactive floors in stack (UI-MAP-L4). */
  dimmed?: boolean;
  interactive?: boolean;
  selectedSceneId?: string | null;
  onSceneClick?: (sceneId: string) => void;
  idPrefix?: string;
};

export function DiagramPlate({
  nodes,
  edges,
  structure,
  tokens,
  dimmed = false,
  interactive = false,
  selectedSceneId = null,
  onSceneClick,
  idPrefix = "plate",
}: Props) {
  const corridors = useMemo(() => computeCorridors(nodes, edges), [nodes, edges]);
  const nodeById = useMemo(() => new Map(nodes.map((n) => [n.sceneId, n])), [nodes]);
  const footprints = useMemo(() => nodes.map((n) => nodeFootprint(n)), [nodes]);
  const plateOpacity = dimmed ? 0.42 : 1;

  const slab = useMemo(() => {
    if (footprints.length === 0) return { x: 0, y: 0, w: 40, h: 30 };
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const fp of footprints) {
      const b = footprintBounds(fp, 3);
      minX = Math.min(minX, b.minX);
      minY = Math.min(minY, b.minY);
      maxX = Math.max(maxX, b.maxX);
      maxY = Math.max(maxY, b.maxY);
    }
    return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
  }, [footprints]);

  const structureId = structure?.structureId ?? nodes[0]?.structureId;

  return (
    <g className="diagram-plate" opacity={plateOpacity}>
      <defs>
        <pattern
          id={`${idPrefix}-grid`}
          width={4}
          height={4}
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 4 0 L 0 0 0 4"
            fill="none"
            stroke="var(--border)"
            strokeWidth={0.06}
            opacity={0.45}
          />
        </pattern>
        <filter id={`${idPrefix}-shadow`} x="-8%" y="-8%" width="116%" height="116%">
          <feDropShadow dx="0" dy="0.6" stdDeviation="0.5" floodOpacity="0.35" />
        </filter>
      </defs>

      {structureId && (
        <g filter={`url(#${idPrefix}-shadow)`}>
          <rect
            x={slab.x}
            y={slab.y}
            width={slab.w}
            height={slab.h}
            fill={`url(#${idPrefix}-grid)`}
            opacity={0.4}
            pointerEvents="none"
          />
          <SmoothEnvelope
            structureId={structureId}
            nodes={nodes}
            boundary={structure?.boundary}
            fill={
              dimmed ? tokens.structureFillOther : tokens.structureFillActive
            }
            stroke={tokens.envelopeStroke}
            strokeWidth={tokens.envelopeStrokeWidth}
            doubleWall={tokens.doubleWall}
          />
        </g>
      )}

      {corridors.map((c) => (
        <CorridorShape key={c.id} x={c.x} y={c.y} w={c.w} h={c.h} tokens={tokens} />
      ))}

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
        const routed = routeEdge(start, end, obstacles, offset, {
          corridors,
          crossesStructure: e.crossesStructure,
          interiorOnly: Boolean(a.structureId) && a.structureId === b.structureId,
        });
        return (
          <path
            key={e.exitId}
            d={routed.pathD}
            fill="none"
            stroke="var(--map-path, var(--border))"
            strokeWidth={0.45}
            opacity={dimmed ? 0.5 : 0.85}
          />
        );
      })}

      {nodes.map((n) => {
        const fp = nodeFootprint(n);
        const active = n.isActive || selectedSceneId === n.sceneId;
        const b = footprintBounds(fp, 0.5);
        return (
          <g key={n.sceneId}>
            {interactive && onSceneClick && (
              <rect
                x={b.minX}
                y={b.minY}
                width={b.maxX - b.minX}
                height={b.maxY - b.minY}
                fill="transparent"
                style={{ cursor: "pointer" }}
                onClick={() => onSceneClick(n.sceneId)}
              />
            )}
            <MapNodeShape
              fp={fp}
              active={active}
              dimmed={dimmed && !active}
              label={n.locationName}
              tokens={tokens}
            />
            {active && (
              <circle
                cx={fp.cx + fp.w * 0.35}
                cy={fp.cy - fp.h * 0.35}
                r={0.9}
                fill="var(--accent)"
                className="diagram-plate__you-are-here"
              />
            )}
          </g>
        );
      })}
    </g>
  );
}
