import { findCorridorForEdge, routeThroughCorridor } from "./corridorGeometry";
import { footprintBounds } from "./layoutGeometry";
import { outdoorWaypoints, smoothCurvePath, smoothQuadraticPath } from "./smoothGeometry";
import type { CorridorSegment, Footprint, Point } from "./types";

export type RoutedEdge = {
  pathD: string;
  labelPoint: Point;
  doorPoint: Point;
  points: Point[];
  outdoor: boolean;
};

function segmentIntersectsRect(
  a: Point,
  b: Point,
  r: { minX: number; minY: number; maxX: number; maxY: number }
): boolean {
  if (a.x >= r.minX && a.x <= r.maxX && a.y >= r.minY && a.y <= r.maxY) return true;
  if (b.x >= r.minX && b.x <= r.maxX && b.y >= r.minY && b.y <= r.maxY) return true;
  const edges: Array<[Point, Point]> = [
    [{ x: r.minX, y: r.minY }, { x: r.maxX, y: r.minY }],
    [{ x: r.maxX, y: r.minY }, { x: r.maxX, y: r.maxY }],
    [{ x: r.maxX, y: r.maxY }, { x: r.minX, y: r.maxY }],
    [{ x: r.minX, y: r.maxY }, { x: r.minX, y: r.minY }],
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
  return t > 0.05 && t < 0.95 && u > 0.05 && u < 0.95;
}

function pathHitsObstacles(points: Point[], obstacles: Footprint[]): boolean {
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    for (const fp of obstacles) {
      const r = footprintBounds(fp, 1.2);
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

function pathToD(points: Point[]): string {
  if (points.length < 2) return "";
  if (points.length === 2) return smoothQuadraticPath(points[0], points[1], 0.12);
  return smoothCurvePath(points, 0.4);
}

function labelOnPath(points: Point[]): Point {
  if (points.length === 2) {
    return {
      x: (points[0].x + points[1].x) / 2,
      y: (points[0].y + points[1].y) / 2,
    };
  }
  const mid = Math.floor(points.length / 2);
  return { ...points[mid] };
}

function doorOnPath(points: Point[]): Point {
  if (points.length < 2) return points[0];
  const a = points[0];
  const b = points[1];
  return { x: a.x + (b.x - a.x) * 0.28, y: a.y + (b.y - a.y) * 0.28 };
}

export type RouteEdgeOptions = {
  obstacles?: Footprint[];
  parallelOffset?: number;
  corridors?: CorridorSegment[];
  crossesStructure?: boolean;
  interiorOnly?: boolean;
};

/** Flowing routes: smooth curves for site paths, short interior links. */
export function routeEdge(
  start: Point,
  end: Point,
  obstacles: Footprint[] = [],
  parallelOffset = 0,
  options: RouteEdgeOptions = {}
): RoutedEdge {
  const { corridors = [], crossesStructure = false, interiorOnly = false } = options;
  const obsRects = obstacles.map((fp) => footprintBounds(fp, 1.5));

  if (interiorOnly && corridors.length > 0) {
    const corridor = findCorridorForEdge(corridors, start, end);
    if (corridor) {
      const via = routeThroughCorridor(start, end, corridor);
      const points = applyParallelOffset(via, parallelOffset);
      return {
        pathD: pathToD(points),
        labelPoint: labelOnPath(points),
        doorPoint: doorOnPath(points),
        points,
        outdoor: false,
      };
    }
  }

  if (interiorOnly) {
    const points = applyParallelOffset([start, end], parallelOffset);
    return {
      pathD: smoothQuadraticPath(points[0], points[1], 0.08),
      labelPoint: labelOnPath(points),
      doorPoint: doorOnPath(points),
      points,
      outdoor: false,
    };
  }

  if (crossesStructure || obstacles.length > 0) {
    const waypoints = outdoorWaypoints(start, end, obsRects);
    let points = applyParallelOffset(waypoints, parallelOffset);
    if (pathHitsObstacles(points, obstacles)) {
      const bulge = Math.hypot(end.x - start.x, end.y - start.y) * 0.28;
      const mx = (start.x + end.x) / 2;
      const my = (start.y + end.y) / 2;
      points = applyParallelOffset(
        [start, { x: mx - bulge, y: my + bulge }, { x: mx + bulge, y: my - bulge }, end],
        parallelOffset
      );
    }
    return {
      pathD: pathToD(points),
      labelPoint: labelOnPath(points),
      doorPoint: doorOnPath(points),
      points,
      outdoor: true,
    };
  }

  const points = applyParallelOffset([start, end], parallelOffset);
  return {
    pathD: smoothQuadraticPath(points[0], points[1], 0.15),
    labelPoint: labelOnPath(points),
    doorPoint: doorOnPath(points),
    points,
    outdoor: false,
  };
}

export function arrowMarkerId(highlighted: boolean): string {
  return highlighted ? "map-arrow-hi" : "map-arrow";
}

/** @deprecated use routeEdge */
export function manhattanPath(start: Point, end: Point): string {
  return routeEdge(start, end, []).pathD;
}
