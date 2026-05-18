import type { SpatialGraph } from "../../api/client";
import { readPlanPosition } from "./diagramModel";
import { nodeFootprint, footprintBounds } from "./layoutGeometry";
import type { MapGraph, MapNode, MapStructure, Point } from "./types";

type Boundary = MapStructure["boundary"];

export function structureCentroid(
  boundary: Boundary,
  nodes: MapNode[]
): Point {
  const b = boundary;
  if (b?.vertices && b.vertices.length >= 3) {
    const xs = b.vertices.map((v) => v.x);
    const ys = b.vertices.map((v) => v.y);
    return {
      x: xs.reduce((a, v) => a + v, 0) / xs.length,
      y: ys.reduce((a, v) => a + v, 0) / ys.length,
    };
  }
  if (b?.cx != null && b?.cy != null) {
    return { x: b.cx, y: b.cy };
  }
  if (b?.x != null && b?.y != null && b?.w != null && b?.h != null) {
    return { x: b.x + b.w / 2, y: b.y + b.h / 2 };
  }
  const group = nodes;
  if (group.length === 0) return { x: 50, y: 50 };
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const n of group) {
    const fp = nodeFootprint(n);
    const box = footprintBounds(fp, 0);
    minX = Math.min(minX, box.minX);
    minY = Math.min(minY, box.minY);
    maxX = Math.max(maxX, box.maxX);
    maxY = Math.max(maxY, box.maxY);
  }
  return { x: (minX + maxX) / 2, y: (minY + maxY) / 2 };
}

function translatePoint(p: Point, dx: number, dy: number): Point {
  return { x: p.x + dx, y: p.y + dy };
}

export function translateBoundary(
  boundary: Boundary,
  dx: number,
  dy: number
): Boundary {
  if (!boundary || (dx === 0 && dy === 0)) return boundary;
  const b = { ...boundary };
  if (b.vertices) {
    b.vertices = b.vertices.map((v) => translatePoint(v, dx, dy));
  }
  if (b.x != null) b.x = b.x + dx;
  if (b.y != null) b.y = b.y + dy;
  if (b.cx != null) b.cx = b.cx + dx;
  if (b.cy != null) b.cy = b.cy + dy;
  return b;
}

function placementMap(worldMap: SpatialGraph["worldMap"]) {
  const m = new Map<string, Point>();
  for (const pl of worldMap?.structurePlacements ?? []) {
    m.set(pl.structureId, pl.origin);
  }
  return m;
}

/** Compose structure-local scene coords into site space using worldMap placements. */
export function applySiteLayout<T extends MapGraph>(graph: T): T {
  const placements = placementMap(graph.worldMap);
  if (placements.size === 0) return graph;

  const structNodes = new Map<string, MapNode[]>();
  for (const n of graph.nodes) {
    if (!n.structureId) continue;
    if (!structNodes.has(n.structureId)) structNodes.set(n.structureId, []);
    structNodes.get(n.structureId)!.push(n);
  }

  const deltas = new Map<string, { dx: number; dy: number }>();
  for (const st of graph.structures ?? []) {
    const origin = placements.get(st.structureId);
    if (!origin) continue;
    const nodes = structNodes.get(st.structureId) ?? [];
    const centroid = structureCentroid(st.boundary, nodes);
    deltas.set(st.structureId, {
      dx: origin.x - centroid.x,
      dy: origin.y - centroid.y,
    });
  }

  if (deltas.size === 0) return graph;

  const nodes = graph.nodes.map((n) => {
    if (!n.structureId) return n;
    const d = deltas.get(n.structureId);
    if (!d) return n;
    const local = readPlanPosition(n);
    const site = { x: local.x + d.dx, y: local.y + d.dy };
    return { ...n, layout: site, planPosition: site };
  });

  const structures = graph.structures?.map((st) => {
    const d = deltas.get(st.structureId);
    if (!d) return st;
    return {
      ...st,
      boundary: translateBoundary(st.boundary, d.dx, d.dy),
    };
  });

  return {
    ...graph,
    nodes,
    structures,
    siteLayoutApplied: true,
  } as T;
}

export function hasSitePlacements(graph: MapGraph): boolean {
  return (graph.worldMap?.structurePlacements?.length ?? 0) > 0;
}

export function structureSiteBounds(
  worldMap: SpatialGraph["worldMap"],
  structures: MapStructure[] | undefined
): { minX: number; minY: number; maxX: number; maxY: number } | null {
  const placements = placementMap(worldMap);
  if (placements.size === 0 || !structures?.length) return null;

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const st of structures) {
    const origin = placements.get(st.structureId);
    if (!origin) continue;
    const env = structureCentroid(st.boundary, []);
    const b = st.boundary;
    if (b?.vertices?.length) {
      for (const v of b.vertices) {
        const sx = origin.x + (v.x - env.x);
        const sy = origin.y + (v.y - env.y);
        minX = Math.min(minX, sx);
        minY = Math.min(minY, sy);
        maxX = Math.max(maxX, sx);
        maxY = Math.max(maxY, sy);
      }
    } else if (b?.cx != null && b?.cy != null && b?.r != null) {
      const cx = origin.x + (b.cx - env.x);
      const cy = origin.y + (b.cy - env.y);
      minX = Math.min(minX, cx - b.r);
      minY = Math.min(minY, cy - b.r);
      maxX = Math.max(maxX, cx + b.r);
      maxY = Math.max(maxY, cy + b.r);
    } else {
      minX = Math.min(minX, origin.x - 8);
      minY = Math.min(minY, origin.y - 8);
      maxX = Math.max(maxX, origin.x + 8);
      maxY = Math.max(maxY, origin.y + 8);
    }
  }

  if (!Number.isFinite(minX)) return null;
  return { minX, minY, maxX, maxY };
}
