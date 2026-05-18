import {
  isoBoundsFromCorners,
  isoFootprintCorners,
  isoPointsToPath,
  isoWallTop,
  planToIso,
} from "./isoProjection";
import type { Footprint, Point } from "./types";

export type DiagramProjection = "plan" | "iso";

export function projectPoint(
  p: Point,
  mode: DiagramProjection,
  origin: Point = { x: 50, y: 50 }
): Point {
  if (mode === "plan") return { x: p.x, y: p.y };
  return planToIso(p.x, p.y, origin);
}

export type ProjectedFootprint = {
  floor: string;
  walls: string;
  labelPt: Point;
  bounds: Point[];
};

export function projectFootprint(
  fp: Footprint,
  mode: DiagramProjection,
  origin: Point
): ProjectedFootprint {
  if (mode === "plan") {
    const x0 = fp.cx - fp.w / 2;
    const x1 = fp.cx + fp.w / 2;
    const y0 = fp.cy - fp.h / 2;
    const y1 = fp.cy + fp.h / 2;
    const corners = [
      { x: x0, y: y0 },
      { x: x1, y: y0 },
      { x: x1, y: y1 },
      { x: x0, y: y1 },
    ];
    return {
      floor: isoPointsToPath(corners),
      walls: "",
      labelPt: { x: fp.cx, y: fp.cy },
      bounds: corners,
    };
  }

  const base = isoFootprintCorners(fp, origin);
  const top = isoWallTop(base);
  const walls = [
    isoPointsToPath([base[0]!, base[1]!, top[1]!, top[0]!]),
    isoPointsToPath([base[1]!, base[2]!, top[2]!, top[1]!]),
    isoPointsToPath([base[2]!, base[3]!, top[3]!, top[2]!]),
  ].join(" ");
  return {
    floor: isoPointsToPath(base),
    walls,
    labelPt: planToIso(fp.cx, fp.cy, origin),
    bounds: [...base, ...top],
  };
}

export function boundsFromProjectedFootprints(
  projected: ProjectedFootprint[],
  pad = 3
): { x: number; y: number; w: number; h: number } {
  const all = projected.flatMap((p) => p.bounds);
  const b = isoBoundsFromCorners(all);
  return {
    x: b.minX - pad,
    y: b.minY - pad,
    w: b.maxX - b.minX + pad * 2,
    h: b.maxY - b.minY + pad * 2,
  };
}

export function plateOriginFromNodes(nodes: { layout?: Point }[]): Point {
  if (nodes.length === 0) return { x: 50, y: 50 };
  let sx = 0;
  let sy = 0;
  for (const n of nodes) {
    sx += n.layout?.x ?? 50;
    sy += n.layout?.y ?? 50;
  }
  return { x: sx / nodes.length, y: sy / nodes.length };
}
