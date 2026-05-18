import { edgeEndpoints } from "./layoutGeometry";
import type { CorridorSegment, MapEdge, MapNode, Point } from "./types";

const CORRIDOR_WIDTH = 2.4;

function corridorRectBetween(start: Point, end: Point): CorridorSegment {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const cx = (start.x + end.x) / 2;
  const cy = (start.y + end.y) / 2;
  if (Math.abs(dx) >= Math.abs(dy)) {
    const w = Math.max(Math.abs(dx), CORRIDOR_WIDTH);
    const h = CORRIDOR_WIDTH;
    return {
      id: `${start.x},${start.y}-${end.x},${end.y}`,
      cx,
      cy,
      x: cx - w / 2,
      y: cy - h / 2,
      w,
      h,
      start,
      end,
    };
  }
  const w = CORRIDOR_WIDTH;
  const h = Math.max(Math.abs(dy), CORRIDOR_WIDTH);
  return {
    id: `${start.x},${start.y}-${end.x},${end.y}`,
    cx,
    cy,
    x: cx - w / 2,
    y: cy - h / 2,
    w,
    h,
    start,
    end,
  };
}

/** Interior same-structure connections → narrow corridor footprints. */
export function computeCorridors(
  nodes: MapNode[],
  edges: MapEdge[]
): CorridorSegment[] {
  const nodeById = new Map(nodes.map((n) => [n.sceneId, n]));
  const seen = new Set<string>();
  const corridors: CorridorSegment[] = [];

  for (const e of edges) {
    if (e.crossesStructure) continue;
    const a = nodeById.get(e.sourceSceneId);
    const b = nodeById.get(e.targetSceneId);
    if (!a || !b || !a.structureId || a.structureId !== b.structureId) continue;
    const key = [e.sourceSceneId, e.targetSceneId].sort().join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    const { start, end } = edgeEndpoints(a, b, e);
    corridors.push(corridorRectBetween(start, end));
  }
  return corridors;
}

export function findCorridorForEdge(
  corridors: CorridorSegment[],
  start: Point,
  end: Point
): CorridorSegment | null {
  for (const c of corridors) {
    const ds = Math.hypot(c.start.x - start.x, c.start.y - start.y);
    const de = Math.hypot(c.end.x - end.x, c.end.y - end.y);
    if (ds < 3 && de < 3) return c;
    const ds2 = Math.hypot(c.start.x - end.x, c.start.y - end.y);
    const de2 = Math.hypot(c.end.x - start.x, c.end.y - start.y);
    if (ds2 < 3 && de2 < 3) return c;
  }
  return null;
}

/** Route through corridor center: start → corridor.start → corridor.end → end. */
export function routeThroughCorridor(
  start: Point,
  end: Point,
  corridor: CorridorSegment
): Point[] {
  const cs = corridor.start;
  const ce = corridor.end;
  if (Math.hypot(start.x - cs.x, start.y - cs.y) < 0.5) {
    return [start, ce, end];
  }
  if (Math.hypot(start.x - ce.x, start.y - ce.y) < 0.5) {
    return [start, cs, end];
  }
  return [start, cs, ce, end];
}

export function corridorFootprint(fp: { cx: number; cy: number; w: number; h: number }) {
  return fp;
}
