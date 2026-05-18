import type { Point } from "./types";

/** Rounded rectangle as SVG path (clockwise). */
export function roundedRectPath(
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
): string {
  const rad = Math.min(r, w / 2, h / 2);
  return [
    `M ${x + rad} ${y}`,
    `L ${x + w - rad} ${y}`,
    `Q ${x + w} ${y} ${x + w} ${y + rad}`,
    `L ${x + w} ${y + h - rad}`,
    `Q ${x + w} ${y + h} ${x + w - rad} ${y + h}`,
    `L ${x + rad} ${y + h}`,
    `Q ${x} ${y + h} ${x} ${y + h - rad}`,
    `L ${x} ${y + rad}`,
    `Q ${x} ${y} ${x + rad} ${y}`,
    "Z",
  ].join(" ");
}

export function circlePath(cx: number, cy: number, r: number): string {
  return `M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy} A ${r} ${r} 0 1 1 ${cx - r} ${cy} Z`;
}

/** Fillet polygon corners for organic structure shells. */
export function smoothPolygonPath(points: Point[], radius = 2.5): string {
  const n = points.length;
  if (n < 3) return "";
  const parts: string[] = [];

  for (let i = 0; i < n; i++) {
    const prev = points[(i - 1 + n) % n];
    const cur = points[i];
    const next = points[(i + 1) % n];

    const v1x = prev.x - cur.x;
    const v1y = prev.y - cur.y;
    const v2x = next.x - cur.x;
    const v2y = next.y - cur.y;
    const len1 = Math.hypot(v1x, v1y) || 1;
    const len2 = Math.hypot(v2x, v2y) || 1;
    const r = Math.min(radius, len1 * 0.4, len2 * 0.4);

    const p1 = { x: cur.x + (v1x / len1) * r, y: cur.y + (v1y / len1) * r };
    const p2 = { x: cur.x + (v2x / len2) * r, y: cur.y + (v2y / len2) * r };

    if (i === 0) parts.push(`M ${p1.x} ${p1.y}`);
    else parts.push(`L ${p1.x} ${p1.y}`);
    parts.push(`Q ${cur.x} ${cur.y} ${p2.x} ${p2.y}`);
  }
  parts.push("Z");
  return parts.join(" ");
}

/** Cubic Catmull-Rom spline through waypoints (open path). */
export function smoothCurvePath(points: Point[], tension = 0.35): string {
  if (points.length < 2) return "";
  if (points.length === 2) {
    return smoothQuadraticPath(points[0], points[1]);
  }

  const parts: string[] = [`M ${points[0].x} ${points[0].y}`];

  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(points.length - 1, i + 2)];

    const c1 = {
      x: p1.x + ((p2.x - p0.x) / 6) * tension * 6,
      y: p1.y + ((p2.y - p0.y) / 6) * tension * 6,
    };
    const c2 = {
      x: p2.x - ((p3.x - p1.x) / 6) * tension * 6,
      y: p2.y - ((p3.y - p1.y) / 6) * tension * 6,
    };
    parts.push(`C ${c1.x} ${c1.y} ${c2.x} ${c2.y} ${p2.x} ${p2.y}`);
  }
  return parts.join(" ");
}

/** Single flowing arc between two points (no hard corners). */
export function smoothQuadraticPath(start: Point, end: Point, bulge = 0.22): string {
  const mx = (start.x + end.x) / 2;
  const my = (start.y + end.y) / 2;
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const dist = Math.hypot(dx, dy) || 1;
  const nx = -dy / dist;
  const ny = dx / dist;
  const bend = dist * bulge;
  const cx = mx + nx * bend;
  const cy = my + ny * bend;
  return `M ${start.x} ${start.y} Q ${cx} ${cy} ${end.x} ${end.y}`;
}

/** Waypoint outside obstacles for outdoor routes. */
export function outdoorWaypoints(
  start: Point,
  end: Point,
  obstacles: Array<{ minX: number; minY: number; maxX: number; maxY: number }>
): Point[] {
  const mx = (start.x + end.x) / 2;
  const my = (start.y + end.y) / 2;
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const perpX = -dy * 0.35;
  const perpY = dx * 0.35;

  const candidates: Point[][] = [
    [start, { x: mx + perpX, y: my + perpY }, end],
    [start, { x: mx - perpX, y: my - perpY }, end],
    [start, { x: start.x + perpX * 0.5, y: start.y + perpY * 0.5 }, { x: end.x + perpX * 0.5, y: end.y + perpY * 0.5 }, end],
    [start, { x: mx, y: start.y }, { x: mx, y: end.y }, end],
  ];

  const hits = (pts: Point[]) => {
    for (let i = 0; i < pts.length - 1; i++) {
      const a = pts[i];
      const b = pts[i + 1];
      for (const r of obstacles) {
        const cx = (a.x + b.x) / 2;
        const cy = (a.y + b.y) / 2;
        if (cx > r.minX && cx < r.maxX && cy > r.minY && cy < r.maxY) return true;
      }
    }
    return false;
  };

  for (const c of candidates) {
    if (!hits(c)) return c;
  }
  return [start, end];
}

export type EnvelopeShape = {
  pathD: string;
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
};

export function envelopeShapeFromBoundary(
  boundary:
    | {
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
      }
    | null
    | undefined,
  fallback: { minX: number; minY: number; maxX: number; maxY: number; vertices?: Point[] }
): EnvelopeShape {
  const b = boundary;
  if (b?.shape === "circle" && b.cx != null && b.cy != null && b.r != null) {
    return {
      pathD: circlePath(b.cx, b.cy, b.r),
      minX: b.cx - b.r,
      minY: b.cy - b.r,
      maxX: b.cx + b.r,
      maxY: b.cy + b.r,
    };
  }
  if (
    (b?.shape === "roundedRect" || b?.shape === "rect") &&
    b.x != null &&
    b.y != null &&
    b.w != null &&
    b.h != null
  ) {
    const rad = b.cornerRadius ?? (b.shape === "roundedRect" ? 4 : 1.5);
    return {
      pathD: roundedRectPath(b.x, b.y, b.w, b.h, rad),
      minX: b.x,
      minY: b.y,
      maxX: b.x + b.w,
      maxY: b.y + b.h,
    };
  }
  if (b?.vertices && b.vertices.length >= 3) {
    const xs = b.vertices.map((v) => v.x);
    const ys = b.vertices.map((v) => v.y);
    return {
      pathD: smoothPolygonPath(b.vertices, b.cornerRadius ?? 3),
      minX: Math.min(...xs),
      minY: Math.min(...ys),
      maxX: Math.max(...xs),
      maxY: Math.max(...ys),
    };
  }
  if (fallback.vertices && fallback.vertices.length >= 3) {
    return {
      pathD: smoothPolygonPath(fallback.vertices, 3),
      minX: fallback.minX,
      minY: fallback.minY,
      maxX: fallback.maxX,
      maxY: fallback.maxY,
    };
  }
  return {
    pathD: roundedRectPath(
      fallback.minX,
      fallback.minY,
      fallback.maxX - fallback.minX,
      fallback.maxY - fallback.minY,
      3.5
    ),
    minX: fallback.minX,
    minY: fallback.minY,
    maxX: fallback.maxX,
    maxY: fallback.maxY,
  };
}
