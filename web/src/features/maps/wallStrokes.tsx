import type { Point } from "./types";

type WallRectProps = {
  x: number;
  y: number;
  w: number;
  h: number;
  rx?: number;
  stroke: string;
  strokeWidth: number;
  dasharray?: string;
  doubleWall?: boolean;
  inset?: number;
};

export function WallRect({
  x,
  y,
  w,
  h,
  rx = 0,
  stroke,
  strokeWidth,
  dasharray,
  doubleWall = false,
  inset = 0.45,
}: WallRectProps) {
  const inner = doubleWall && w > inset * 3 && h > inset * 3;
  return (
    <g className="map-wall">
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={rx}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeDasharray={dasharray}
      />
      {inner && (
        <rect
          x={x + inset}
          y={y + inset}
          width={w - inset * 2}
          height={h - inset * 2}
          rx={Math.max(0, rx - inset * 0.5)}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth * 0.65}
          strokeDasharray={dasharray}
          opacity={0.75}
        />
      )}
    </g>
  );
}

type WallPolygonProps = {
  points: Point[];
  stroke: string;
  strokeWidth: number;
  dasharray?: string;
  doubleWall?: boolean;
};

/** Inset polygon toward centroid for inner wall line. */
function insetPolygon(points: Point[], inset: number): Point[] {
  const cx = points.reduce((s, p) => s + p.x, 0) / points.length;
  const cy = points.reduce((s, p) => s + p.y, 0) / points.length;
  return points.map((p) => {
    const dx = cx - p.x;
    const dy = cy - p.y;
    const len = Math.hypot(dx, dy) || 1;
    return { x: p.x + (dx / len) * inset, y: p.y + (dy / len) * inset };
  });
}

export function WallPolygon({
  points,
  stroke,
  strokeWidth,
  dasharray,
  doubleWall = false,
}: WallPolygonProps) {
  const pts = points.map((p) => `${p.x},${p.y}`).join(" ");
  const inner = doubleWall ? insetPolygon(points, 0.55) : null;
  return (
    <g className="map-wall">
      <polygon points={pts} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeDasharray={dasharray} />
      {inner && (
        <polygon
          points={inner.map((p) => `${p.x},${p.y}`).join(" ")}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth * 0.65}
          strokeDasharray={dasharray}
          opacity={0.75}
        />
      )}
    </g>
  );
}
