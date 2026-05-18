import { useMemo } from "react";
import { computeCorridors } from "./corridorGeometry";
import { projectFootprint, plateOriginFromNodes, boundsFromProjectedFootprints } from "./diagramProjection";
import { edgeEndpoints, hubEdgeIndex, nodeFootprint } from "./layoutGeometry";
import { routeEdge } from "./edgeRouting";
import { isoPointsToPath } from "./isoProjection";
import type { MapStyleTokens } from "./mapStyle";
import type { MapEdge, MapNode, MapStructure } from "./types";

type Props = {
  nodes: MapNode[];
  edges: MapEdge[];
  structure?: MapStructure;
  tokens: MapStyleTokens;
  /** @deprecated structure kept for API parity with DiagramPlate */
  dimmed?: boolean;
  interactive?: boolean;
  selectedSceneId?: string | null;
  onSceneClick?: (sceneId: string) => void;
  idPrefix?: string;
};

function truncate(name: string, max = 10): string {
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

export function IsoDiagramPlate({
  nodes,
  edges,
  structure: _structure,
  tokens,
  dimmed = false,
  interactive = false,
  selectedSceneId = null,
  onSceneClick,
  idPrefix = "iso",
}: Props) {
  const origin = useMemo(() => plateOriginFromNodes(nodes), [nodes]);
  const plateOpacity = dimmed ? 0.42 : 1;
  const { floorPath, rooms } = useMemo(() => {
    const projected = nodes.map((n) => ({
      node: n,
      ...projectFootprint(nodeFootprint(n), "iso", origin),
    }));
    const bounds = boundsFromProjectedFootprints(projected);
    const pad = 2;
    const floorPath = isoPointsToPath([
      { x: bounds.x - pad, y: bounds.y - pad },
      { x: bounds.x + bounds.w + pad, y: bounds.y - pad },
      { x: bounds.x + bounds.w + pad, y: bounds.y + bounds.h + pad },
      { x: bounds.x - pad, y: bounds.y + bounds.h + pad },
    ]);
    const rooms = projected.map(({ node, floor, walls, labelPt }) => ({
      sceneId: node.sceneId,
      floor,
      walls,
      labelPt,
      label: truncate(node.locationName).toUpperCase(),
      active: Boolean(node.isActive || selectedSceneId === node.sceneId),
    }));
    return { floorPath, rooms };
  }, [nodes, origin, selectedSceneId]);

  const corridors = useMemo(() => computeCorridors(nodes, edges), [nodes, edges]);
  const nodeById = useMemo(() => new Map(nodes.map((n) => [n.sceneId, n])), [nodes]);
  const footprints = useMemo(() => nodes.map((n) => nodeFootprint(n)), [nodes]);

  return (
    <g className="iso-plate" opacity={plateOpacity}>
      <defs>
        <pattern
          id={`${idPrefix}-grid`}
          width={2.8}
          height={2.8}
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 2.8 0 L 0 0 0 2.8"
            fill="none"
            stroke="var(--border)"
            strokeWidth={0.07}
            opacity={0.4}
          />
        </pattern>
        <filter id={`${idPrefix}-shadow`} x="-10%" y="-10%" width="120%" height="120%">
          <feDropShadow dx="0" dy="0.5" stdDeviation="0.45" floodOpacity="0.4" />
        </filter>
      </defs>

      <g filter={`url(#${idPrefix}-shadow)`}>
        <path
          d={floorPath}
          fill={`url(#${idPrefix}-grid)`}
          stroke={tokens.envelopeStroke}
          strokeWidth={tokens.envelopeStrokeWidth * 0.75}
        />
      </g>

      {edges.map((e) => {
        const a = nodeById.get(e.sourceSceneId);
        const b = nodeById.get(e.targetSceneId);
        if (!a?.layout || !b?.layout) return null;
        const { start, end } = edgeEndpoints(a, b, e);
        const obstacles = footprints.filter(
          (fp) => fp.sceneId !== a.sceneId && fp.sceneId !== b.sceneId
        );
        const { index, total } = hubEdgeIndex(edges, e.exitId);
        const offset = total > 1 ? (index - (total - 1) / 2) * 1.2 : 0;
        const routed = routeEdge(start, end, obstacles, offset, {
          corridors,
          interiorOnly: true,
        });
        return (
          <path
            key={e.exitId}
            d={routed.pathD}
            fill="none"
            stroke="var(--map-path, var(--border))"
            strokeWidth={0.35}
            opacity={dimmed ? 0.45 : 0.7}
          />
        );
      })}

      {rooms.map((room) => (
        <g
          key={room.sceneId}
          className={room.active ? "iso-room iso-room--active" : "iso-room"}
          role={interactive && onSceneClick ? "button" : undefined}
          tabIndex={interactive && onSceneClick ? 0 : undefined}
          style={{ cursor: interactive && onSceneClick ? "pointer" : undefined }}
          onClick={interactive && onSceneClick ? () => onSceneClick(room.sceneId) : undefined}
        >
          <path d={room.floor} fill={room.active ? tokens.roomFillActive : tokens.roomFill} opacity={0.88} />
          {room.walls && (
            <path
              d={room.walls}
              fill={tokens.envelopeStroke}
              opacity={0.5}
              stroke={tokens.roomStroke}
              strokeWidth={0.12}
            />
          )}
          {room.active && (
            <path
              d={room.floor}
              fill="none"
              stroke="var(--accent)"
              strokeWidth={0.32}
              className="iso-room__active-ring"
            />
          )}
          <text
            x={room.labelPt.x}
            y={room.labelPt.y}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={1.75}
            className="iso-room__label"
            fill="var(--fg)"
          >
            {room.label}
          </text>
          {room.active && (
            <circle
              cx={room.labelPt.x + 3.5}
              cy={room.labelPt.y - 2}
              r={0.85}
              fill="var(--accent)"
              className="diagram-plate__you-are-here"
            />
          )}
        </g>
      ))}
    </g>
  );
}

export function isoPlateViewBox(nodes: MapNode[], pad = 4) {
  const origin = plateOriginFromNodes(nodes);
  const projected = nodes.map((n) => projectFootprint(nodeFootprint(n), "iso", origin));
  return boundsFromProjectedFootprints(projected, pad);
}
