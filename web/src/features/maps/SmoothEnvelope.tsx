import { envelopeShapeFromBoundary } from "./smoothGeometry";
import type { MapNode, Point } from "./types";
import { structureEnvelope } from "./layoutGeometry";

type Boundary = {
  shape?: string;
  vertices?: Point[];
  x?: number;
  y?: number;
  w?: number;
  h?: number;
  cx?: number;
  cy?: number;
  r?: number;
  cornerRadius?: number;
} | null;

type Props = {
  structureId: string;
  nodes: MapNode[];
  boundary?: Boundary;
  fill?: string;
  stroke?: string;
  strokeWidth?: number;
  dasharray?: string;
  doubleWall?: boolean;
  className?: string;
};

export function getEnvelopePath(
  structureId: string,
  nodes: MapNode[],
  boundary?: Boundary
) {
  const raw = structureEnvelope(structureId, nodes, boundary);
  if (!raw) return null;
  return envelopeShapeFromBoundary(boundary, raw);
}

export function SmoothEnvelope({
  structureId,
  nodes,
  boundary,
  fill,
  stroke,
  strokeWidth = 0.7,
  dasharray,
  doubleWall = false,
  className = "map-envelope",
}: Props) {
  const shape = getEnvelopePath(structureId, nodes, boundary);
  if (!shape) return null;

  return (
    <g className={className}>
      {fill && fill !== "none" && (
        <path d={shape.pathD} fill={fill} stroke="none" />
      )}
      <path
        d={shape.pathD}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeDasharray={dasharray}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {doubleWall && stroke && (
        <path
          d={shape.pathD}
          fill="none"
          stroke={stroke}
          strokeWidth={Math.max(0.25, strokeWidth * 0.45)}
          strokeDasharray={dasharray}
          strokeLinejoin="round"
          strokeLinecap="round"
          opacity={0.5}
        />
      )}
    </g>
  );
}
