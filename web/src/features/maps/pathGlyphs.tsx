import type { Point } from "./types";

type DoorGlyphProps = {
  point: Point;
  angleDeg: number;
  highlighted?: boolean;
};

/** Door: gap tick across wall (interior). */
export function DoorGlyph({ point, angleDeg, highlighted }: DoorGlyphProps) {
  const stroke = highlighted ? "var(--active-scene)" : "var(--map-wall, var(--border))";
  const rad = (angleDeg * Math.PI) / 180;
  const len = 1.6;
  const dx = Math.cos(rad) * len;
  const dy = Math.sin(rad) * len;
  return (
    <g className="map-door-glyph" transform={`translate(${point.x}, ${point.y})`}>
      <line x1={-dx} y1={-dy} x2={dx} y2={dy} stroke={stroke} strokeWidth={0.55} />
      <line
        x1={-dy * 0.35}
        y1={dx * 0.35}
        x2={dy * 0.35}
        y2={-dx * 0.35}
        stroke={stroke}
        strokeWidth={0.35}
      />
    </g>
  );
}

type GateGlyphProps = {
  point: Point;
  angleDeg: number;
  highlighted?: boolean;
};

/** Gate bracket on cross-structure path. */
export function GateGlyph({ point, angleDeg, highlighted }: GateGlyphProps) {
  const stroke = highlighted ? "var(--active-scene)" : "var(--map-wall, var(--border))";
  const rad = (angleDeg * Math.PI) / 180;
  const nx = Math.cos(rad);
  const ny = Math.sin(rad);
  const px = -ny;
  const py = nx;
  const s = 1.2;
  return (
    <g className="map-gate-glyph" transform={`translate(${point.x}, ${point.y})`}>
      <line x1={-px * s} y1={-py * s} x2={px * s} y2={py * s} stroke={stroke} strokeWidth={0.6} />
      <line x1={-nx * s * 0.5} y1={-ny * s * 0.5} x2={nx * s * 0.5} y2={ny * s * 0.5} stroke={stroke} strokeWidth={0.45} />
    </g>
  );
}

export function pathAngleAtPoint(points: Point[], idx: number): number {
  const a = points[Math.max(0, idx - 1)];
  const b = points[Math.min(points.length - 1, idx + 1)];
  return (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI;
}
