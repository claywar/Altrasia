import { footprintBounds } from "./layoutGeometry";
import type { Footprint, Point } from "./types";

export type RoutedEdge = {
  pathD: string;
  labelPoint: Point;
  doorPoint: Point;
  points: Point[];
};

function segmentIntersectsRect(
  a: Point,
  b: Point,
  r: { minX: number; minY: number; maxX: number; maxY: number }
): boolean {
  if (a.x >= r.minX && a.x <= r.maxX && a.y >= r.minY && a.y <= r.maxY) return true;
  if (b.x >= r.minX && b.x <= r.maxX && b.y >= r.minY && b.y <= r.maxY) return true;
  const left = r.minX;
  const right = r.maxX;
  const top = r.minY;
  const bottom = r.maxY;
  const edges: Array<[Point, Point]> = [
    [{ x: left, y: top }, { x: right, y: top }],
    [{ x: right, y: top }, { x: right, y: bottom }],
    [{ x: right, y: bottom }, { x: left, y: bottom }],
    [{ x: left, y: bottom }, { x: left, y: top }],
  ];
  for (const [p1, p2] of edges) {
    if (segmentsIntersect(a, b, p1, p2)) return true;
  }
  return false;
}

function segmentsIntersect(a: Point, b: Point, c: Point, d: Point): boolean {
  const det = (b.x - a.x) * (d.y - c.y) - (b.y - a.y) * (d.x - c.x);
  if (Math.abs(det) < 1e-9) return false;
  const t = ((c.x - a.x) * (d.y - c.y) - (c.y - a.y) * (d.x - c.x)) / det;
  const u = ((c.x - a.x) * (b.y - a.y) - (c.y - a.y) * (b.x - a.x)) / det;
  return t > 0.02 && t < 0.98 && u > 0.02 && u < 0.98;
}

function pathHitsObstacles(points: Point[], obstacles: Footprint[]): boolean {
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    for (const fp of obstacles) {
      const r = footprintBounds(fp, 0.8);
      if (segmentIntersectsRect(a, b, r)) return true;
    }
  }
  return false;
}

function applyParallelOffset(points: Point[], offset: number): Point[] {
  if (points.length < 2 || offset === 0) return points;
  const out = points.map((p) => ({ ...p }));
  for (let i = 1; i < out.length - 1; i++) {
    const prev = out[i - 1];
    const cur = out[i];
    const next = out[i + 1];
    const dx1 = cur.x - prev.x;
    const dy1 = cur.y - prev.y;
    const dx2 = next.x - cur.x;
    const dy2 = next.y - cur.y;
    const len1 = Math.hypot(dx1, dy1) || 1;
    const len2 = Math.hypot(dx2, dy2) || 1;
    const nx = (-dy1 / len1 + -dy2 / len2) / 2;
    const ny = (dx1 / len1 + dx2 / len2) / 2;
    const nlen = Math.hypot(nx, ny) || 1;
    out[i] = { x: cur.x + (nx / nlen) * offset, y: cur.y + (ny / nlen) * offset };
  }
  return out;
}

function buildCandidatePaths(start: Point, end: Point): Point[][] {
  const midH: Point = { x: end.x, y: start.y };
  const midV: Point = { x: start.x, y: end.y };
  const direct =
    Math.abs(start.x - end.x) < 0.5 || Math.abs(start.y - end.y) < 0.5
      ? [start, end]
      : null;
  const paths: Point[][] = [];
  if (direct) paths.push(direct);
  paths.push([start, midH, end]);
  paths.push([start, midV, end]);
  if (!direct) {
    const gutterY = (start.y + end.y) / 2;
    const gutterX = (start.x + end.x) / 2;
    paths.push([start, { x: start.x, y: gutterY }, { x: end.x, y: gutterY }, end]);
    paths.push([start, { x: gutterX, y: start.y }, { x: gutterX, y: end.y }, end]);
  }
  return paths;
}

function pathToD(points: Point[]): string {
  if (points.length < 2) return "";
  return points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
}

function labelOnPath(points: Point[]): Point {
  if (points.length === 2) {
    return {
      x: (points[0].x + points[1].x) / 2,
      y: (points[0].y + points[1].y) / 2,
    };
  }
  const midIdx = Math.floor((points.length - 1) / 2);
  const a = points[midIdx];
  const b = points[midIdx + 1];
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

function doorOnPath(points: Point[]): Point {
  if (points.length < 2) return points[0];
  const a = points[0];
  const b = points[1];
  return { x: a.x + (b.x - a.x) * 0.35, y: a.y + (b.y - a.y) * 0.35 };
}

/** Route edge with obstacle avoidance and optional hub offset (UI-MAP-R9, R2). */
export function routeEdge(
  start: Point,
  end: Point,
  obstacles: Footprint[],
  parallelOffset = 0
): RoutedEdge {
  const candidates = buildCandidatePaths(start, end);
  let best: Point[] = candidates[0];
  for (const cand of candidates) {
    if (!pathHitsObstacles(cand, obstacles)) {
      best = cand;
      break;
    }
  }
  const points = applyParallelOffset(best, parallelOffset);
  return {
    pathD: pathToD(points),
    labelPoint: labelOnPath(points),
    doorPoint: doorOnPath(points),
    points,
  };
}

export function arrowMarkerId(highlighted: boolean): string {
  return highlighted ? "map-arrow-hi" : "map-arrow";
}

/** @deprecated use routeEdge */
export function manhattanPath(start: Point, end: Point): string {
  return routeEdge(start, end, []).pathD;
}
