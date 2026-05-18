import type { Footprint, MapEdge, MapGraph, MapNode, Point } from "./types";

const DEFAULT_W = 12;
const DEFAULT_H = 8;
const CIRCLE_R = 5;

export function nodeFootprint(node: MapNode): Footprint {
  const cx = node.layout?.x ?? 50;
  const cy = node.layout?.y ?? 50;
  const shape = node.mapShape ?? "rect";
  if (shape === "circle") {
    return { cx, cy, w: CIRCLE_R * 2, h: CIRCLE_R * 2, shape, sceneId: node.sceneId };
  }
  const sz = node.mapSize;
  const w = sz?.w ?? DEFAULT_W;
  const h = sz?.h ?? DEFAULT_H;
  if (shape === "corridor") {
    return { cx, cy, w: Math.max(w, 6), h: Math.min(h ?? 4, 5), shape, sceneId: node.sceneId };
  }
  return { cx, cy, w, h, shape, sceneId: node.sceneId };
}

export function footprintBounds(fp: Footprint, pad = 1) {
  return {
    minX: fp.cx - fp.w / 2 - pad,
    maxX: fp.cx + fp.w / 2 + pad,
    minY: fp.cy - fp.h / 2 - pad,
    maxY: fp.cy + fp.h / 2 + pad,
  };
}

export function anchorOnFootprint(fp: Footprint, anchor?: string): Point {
  const side = anchor?.[0]?.toUpperCase() ?? "C";
  const { cx, cy, w, h } = fp;
  if (side === "N") return { x: cx, y: cy - h / 2 };
  if (side === "S") return { x: cx, y: cy + h / 2 };
  if (side === "E") return { x: cx + w / 2, y: cy };
  if (side === "W") return { x: cx - w / 2, y: cy };
  return { x: cx, y: cy };
}

/** Endpoints on footprint rims; travelSteps is visual-only (badge/stroke). */
export function edgeEndpoints(
  source: MapNode,
  target: MapNode,
  edge: MapEdge
): { start: Point; end: Point } {
  const sFp = nodeFootprint(source);
  const tFp = nodeFootprint(target);
  const anchor = edge.exitAnchor ?? inferAnchorFromDirection(edge.direction, source, target);
  const start = anchorOnFootprint(sFp, anchor);
  const endAnchor =
    edge.crossesStructure && target.structureId !== source.structureId
      ? inferAnchorFromDirection(edge.direction, target, source) ?? oppositeAnchor(anchor)
      : oppositeAnchor(anchor);
  const end = anchorOnFootprint(tFp, endAnchor ?? oppositeAnchor(anchor));
  return { start, end };
}

function inferAnchorFromDirection(
  direction: string | undefined,
  source: MapNode,
  target: MapNode
): string | undefined {
  if (direction) {
    const d = direction.toUpperCase();
    if (d.includes("N")) return "N";
    if (d.includes("S")) return "S";
    if (d.includes("E")) return "E";
    if (d.includes("W")) return "W";
  }
  const sx = source.layout?.x ?? 0;
  const sy = source.layout?.y ?? 0;
  const tx = target.layout?.x ?? 0;
  const ty = target.layout?.y ?? 0;
  const adx = Math.abs(tx - sx);
  const ady = Math.abs(ty - sy);
  if (ady > adx) return ty < sy ? "N" : "S";
  return tx < sx ? "W" : "E";
}

export function oppositeAnchor(anchor?: string): string | undefined {
  const s = anchor?.[0]?.toUpperCase();
  if (s === "N") return "S";
  if (s === "S") return "N";
  if (s === "E") return "W";
  if (s === "W") return "E";
  return undefined;
}

export function structureEnvelope(
  structureId: string,
  nodes: MapNode[],
  boundary?: MapGraph["structures"] extends (infer S)[] | undefined
    ? S extends { boundary?: infer B }
      ? B
      : never
    : never
): { minX: number; minY: number; maxX: number; maxY: number; vertices?: Point[] } | null {
  const group = nodes.filter((n) => n.structureId === structureId);
  if (group.length === 0) return null;

  const b = boundary as
    | { shape?: string; vertices?: Point[]; x?: number; y?: number; w?: number; h?: number }
    | null
    | undefined;
  if (b?.vertices && b.vertices.length >= 3) {
    const xs = b.vertices.map((v) => v.x);
    const ys = b.vertices.map((v) => v.y);
    return {
      minX: Math.min(...xs),
      minY: Math.min(...ys),
      maxX: Math.max(...xs),
      maxY: Math.max(...ys),
      vertices: b.vertices,
    };
  }
  if (b?.x != null && b?.w != null && b?.y != null && b?.h != null) {
    return { minX: b.x, minY: b.y, maxX: b.x + b.w, maxY: b.y + b.h };
  }

  const pad = 4;
  const fws = group.map((n) => nodeFootprint(n));
  const minX = Math.min(...fws.map((f) => f.cx - f.w / 2)) - pad;
  const maxX = Math.max(...fws.map((f) => f.cx + f.w / 2)) + pad;
  const minY = Math.min(...fws.map((f) => f.cy - f.h / 2)) - pad;
  const maxY = Math.max(...fws.map((f) => f.cy + f.h / 2)) + pad;
  return { minX, minY, maxX, maxY };
}

export type ZoneBand = {
  key: string;
  structureId: string;
  mapZone: string;
  minX: number;
  maxX: number;
  bandY: number;
  nodes: MapNode[];
};

/** Zone bands scoped per structure (UI-MAP-R5). */
export function zoneBandsFromNodes(nodes: MapNode[]): ZoneBand[] {
  const groups = new Map<string, MapNode[]>();
  for (const n of nodes) {
    const z = n.mapZone ?? "";
    if (!z) continue;
    const sid = n.structureId ?? "_none";
    const key = `${sid}::${z}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(n);
  }
  const bands: ZoneBand[] = [];
  for (const [key, zn] of groups) {
    const [structureId, mapZone] = key.split("::");
    const fws = zn.map((n) => nodeFootprint(n));
    const minX = Math.min(...fws.map((f) => f.cx - f.w / 2)) - 2;
    const maxX = Math.max(...fws.map((f) => f.cx + f.w / 2)) + 2;
    const bandY = Math.min(...zn.map((n) => n.layout?.y ?? 50)) - 6;
    bands.push({ key, structureId, mapZone, minX, maxX, bandY, nodes: zn });
  }
  return bands;
}

export function neighborSceneIds(
  graph: MapGraph,
  focusId: string,
  maxHops = 2
): Set<string> {
  const adj = new Map<string, string[]>();
  for (const n of graph.nodes) adj.set(n.sceneId, []);
  for (const e of graph.edges) {
    adj.get(e.sourceSceneId)?.push(e.targetSceneId);
    adj.get(e.targetSceneId)?.push(e.sourceSceneId);
  }
  const seen = new Set<string>([focusId]);
  const q: Array<[string, number]> = [[focusId, 0]];
  while (q.length) {
    const [id, d] = q.shift()!;
    if (d >= maxHops) continue;
    for (const nb of adj.get(id) ?? []) {
      if (!seen.has(nb)) {
        seen.add(nb);
        q.push([nb, d + 1]);
      }
    }
  }
  return seen;
}

export function computeNeighborhoodDim(graph: MapGraph): Map<string, boolean> {
  const dimmed = new Map<string, boolean>();
  const active = graph.nodes.find((n) => n.isActive)?.sceneId;
  if (!active || graph.nodes.length <= 8) return dimmed;

  const seen = neighborSceneIds(graph, active, 2);
  for (const n of graph.nodes) {
    if (!seen.has(n.sceneId)) dimmed.set(n.sceneId, true);
  }
  return dimmed;
}

export function hasDirectionalEdges(edges: MapEdge[]): boolean {
  return edges.some((e) => e.direction);
}

/** Count edges sharing same source for parallel offset. */
export function hubEdgeIndex(edges: MapEdge[], exitId: string): { index: number; total: number } {
  const e = edges.find((x) => x.exitId === exitId);
  if (!e) return { index: 0, total: 1 };
  const siblings = edges.filter((x) => x.sourceSceneId === e.sourceSceneId);
  siblings.sort((a, b) => a.exitId.localeCompare(b.exitId));
  return { index: siblings.findIndex((x) => x.exitId === exitId), total: siblings.length };
}
