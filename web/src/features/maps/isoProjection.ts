import type { Footprint, Point } from "./types";

/** Dimetric projection for schematic stack plates (not walkable 3D). */
const ISO_X = 0.866;
const ISO_Y = 0.5;
const ISO_SCALE = 0.52;
const WALL_RISE = 2.8;

export function planToIso(
  x: number,
  y: number,
  origin: Point = { x: 50, y: 50 }
): Point {
  const px = (x - origin.x) * ISO_SCALE;
  const py = (y - origin.y) * ISO_SCALE;
  return { x: (px - py) * ISO_X, y: (px + py) * ISO_Y };
}

export function isoFootprintCorners(fp: Footprint, origin: Point): [Point, Point, Point, Point] {
  const x0 = fp.cx - fp.w / 2;
  const x1 = fp.cx + fp.w / 2;
  const y0 = fp.cy - fp.h / 2;
  const y1 = fp.cy + fp.h / 2;
  return [
    planToIso(x0, y0, origin),
    planToIso(x1, y0, origin),
    planToIso(x1, y1, origin),
    planToIso(x0, y1, origin),
  ];
}

export function isoWallTop(corners: Point[]): Point[] {
  return corners.map((c) => ({ x: c.x, y: c.y - WALL_RISE }));
}

export function isoPointsToPath(points: Point[], close = true): string {
  if (points.length === 0) return "";
  const head = `M ${points[0]!.x} ${points[0]!.y}`;
  const rest = points.slice(1).map((p) => `L ${p.x} ${p.y}`).join(" ");
  return close ? `${head} ${rest} Z` : `${head} ${rest}`;
}

export function isoBoundsFromCorners(all: Point[]): {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
} {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const p of all) {
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x);
    maxY = Math.max(maxY, p.y);
  }
  if (!Number.isFinite(minX)) {
    return { minX: 0, minY: 0, maxX: 40, maxY: 24 };
  }
  return { minX, minY, maxX, maxY };
}
