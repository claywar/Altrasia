import type { NavigationRoute, SpatialGraph } from "../../api/client";
import type { MapViewMode } from "../maps/floorLevels";
import { edgeEndpoints, nodeFootprint, oppositeAnchor } from "../maps/layoutGeometry";
import { readPlanPosition } from "../maps/diagramModel";
import { applySiteLayout } from "../maps/worldSiteLayout";
import type { MapEdge, MapNode } from "../maps/types";
import {
  FLOOR_HEIGHT,
  planToWorldXz,
  PLAN_SCALE,
  position3dToWorldXz,
  referencePointToWorld,
  worldYFromLevel,
} from "./coordinates";

export { FLOOR_HEIGHT, PLAN_SCALE };
export const WALL_HEIGHT = 2.35;
export const WALL_THICK = 0.14;
export const FLOOR_SLAB = 0.1;
export const DOOR_HEIGHT = 1.05;
export const PARAPET_HEIGHT = 0.85;

export type RoomMesh = {
  sceneId: string;
  locationName: string;
  /** Floor origin (center XZ, base Y). */
  position: [number, number, number];
  size: [number, number, number];
  shape: string;
  isActive: boolean;
  structureId?: string;
  levelIndex: number;
  levelLabel?: string;
  wallHeight: number;
  isOutdoor: boolean;
  dimmed?: boolean;
};

export type SceneGraphViewFilter = {
  context?: MapViewMode;
  structureId?: string;
  level?: number;
};

export type EdgeSegment = {
  exitId?: string;
  from: [number, number, number];
  to: [number, number, number];
  onRoute: boolean;
  vertical: boolean;
  label?: string;
  targetSceneId?: string;
};

export type StructurePad = {
  structureId: string;
  displayName: string;
  footprint: Array<[number, number]>;
  center: [number, number, number];
  kind?: string;
  containsActive: boolean;
  maxLevel: number;
  isOutdoor: boolean;
};

export type ReferenceMarker = {
  id: string;
  label: string;
  position: [number, number, number];
  sceneId?: string;
};

export type SceneGraph3D = {
  rooms: RoomMesh[];
  edges: EdgeSegment[];
  structures: StructurePad[];
  references: ReferenceMarker[];
  hiddenWalls: Record<string, Set<string>>;
  siteCenter: [number, number, number];
  bounds: { min: [number, number, number]; max: [number, number, number] };
};

/** Omit interior wall faces shared between same-floor rooms. */
export function computeHiddenWalls(
  nodes: MapNode[],
  edges: MapEdge[]
): Record<string, Set<string>> {
  const nodeById = new Map(nodes.map((n) => [n.sceneId, n]));
  const hidden: Record<string, Set<string>> = {};

  const add = (sceneId: string, side: string) => {
    if (!hidden[sceneId]) hidden[sceneId] = new Set();
    hidden[sceneId].add(side);
  };

  for (const e of edges) {
    if (e.crossesStructure) continue;
    const src = nodeById.get(e.sourceSceneId);
    const tgt = nodeById.get(e.targetSceneId);
    if (!src || !tgt || !src.structureId || src.structureId !== tgt.structureId) continue;
    if (nodeLevel(src) !== nodeLevel(tgt)) continue;
    const { start } = edgeEndpoints(src, tgt, e);
    const sFp = nodeFootprint(src);
    const anchor =
      e.exitAnchor ??
      (Math.abs(start.y - (sFp.cy - sFp.h / 2)) < 0.5
        ? "N"
        : Math.abs(start.y - (sFp.cy + sFp.h / 2)) < 0.5
          ? "S"
          : Math.abs(start.x - (sFp.cx + sFp.w / 2)) < 0.5
            ? "E"
            : "W");
    const side = anchor?.[0]?.toUpperCase();
    if (!side || side === "C") continue;
    add(src.sceneId, side);
    const opp = oppositeAnchor(side);
    if (opp) add(tgt.sceneId, opp);
  }
  return hidden;
}

const STRUCTURE_COLORS: Record<string, string> = {
  manor: "#6b5a4a",
  keep: "#5a6472",
  bailey: "#3f5c44",
};

export function structureColor(structureId?: string): string {
  if (!structureId) return "#4a5568";
  return STRUCTURE_COLORS[structureId] ?? "#4a5568";
}

function planToWorld(x: number, y: number): [number, number] {
  return planToWorldXz(x, y);
}

function floorY(level: number): number {
  return worldYFromLevel(level);
}

function structureFootprint(
  boundary: NonNullable<SpatialGraph["structures"]>[0]["boundary"]
): Array<[number, number]> {
  if (!boundary) return [];
  if (boundary.vertices?.length) {
    return boundary.vertices.map((v) => planToWorld(v.x, v.y));
  }
  if (boundary.cx != null && boundary.cy != null && boundary.r != null) {
    const pts: Array<[number, number]> = [];
    for (let i = 0; i < 24; i++) {
      const a = (i / 24) * Math.PI * 2;
      const [wx, wz] = planToWorld(
        boundary.cx + Math.cos(a) * boundary.r,
        boundary.cy + Math.sin(a) * boundary.r
      );
      pts.push([wx, wz]);
    }
    return pts;
  }
  if (boundary.x != null && boundary.y != null && boundary.w != null && boundary.h != null) {
    const x0 = boundary.x;
    const y0 = boundary.y;
    const x1 = x0 + boundary.w;
    const y1 = y0 + boundary.h;
    return [
      planToWorld(x0, y0),
      planToWorld(x1, y0),
      planToWorld(x1, y1),
      planToWorld(x0, y1),
    ];
  }
  return [];
}

/** Convex hull envelope from grouped rooms when no authored boundary exists. */
function structureFootprintFromRooms(roomNodes: MapNode[]): Array<[number, number]> {
  if (!roomNodes.length) return [];
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const pad = 3;
  for (const n of roomNodes) {
    const fp = nodeFootprint(n);
    minX = Math.min(minX, fp.cx - fp.w / 2);
    minY = Math.min(minY, fp.cy - fp.h / 2);
    maxX = Math.max(maxX, fp.cx + fp.w / 2);
    maxY = Math.max(maxY, fp.cy + fp.h / 2);
  }
  return [
    planToWorld(minX - pad, minY - pad),
    planToWorld(maxX + pad, minY - pad),
    planToWorld(maxX + pad, maxY + pad),
    planToWorld(minX - pad, maxY + pad),
  ];
}

function nodeLevel(n: MapNode): number {
  return n.levelIndex ?? n.mapLevel ?? 0;
}

function roomFromNode(n: MapNode, structureKinds: Map<string, string>): RoomMesh {
  const plan = readPlanPosition(n);
  const p3 = (n as MapNode & { position3d?: { x: number; y: number; z: number } }).position3d;
  const [wx, wz] = p3 ? position3dToWorldXz(p3) : planToWorld(plan.x, plan.y);
  const fp = nodeFootprint({ ...n, layout: { x: plan.x, y: plan.y } });
  const lvl = nodeLevel(n);
  const kind = n.structureId ? structureKinds.get(n.structureId) : undefined;
  const isOutdoor = kind === "outdoor";
  const shape = fp.shape ?? "rect";
  const w = Math.max(fp.w * PLAN_SCALE, 0.9);
  const d = Math.max(fp.h * PLAN_SCALE, 0.7);
  let wallHeight = WALL_HEIGHT;
  if (isOutdoor) wallHeight = PARAPET_HEIGHT;
  else if (shape === "corridor") wallHeight = WALL_HEIGHT * 0.72;

  return {
    sceneId: n.sceneId,
    locationName: n.locationName,
    position: [wx, floorY(lvl), wz],
    size: [w, wallHeight, d],
    shape,
    isActive: n.isActive,
    structureId: n.structureId,
    levelIndex: lvl,
    levelLabel: n.levelLabel,
    wallHeight,
    isOutdoor,
  };
}

function roomDimmed(
  room: RoomMesh,
  filter: SceneGraphViewFilter | undefined,
  nodeById: Map<string, MapNode>
): boolean {
  if (!filter?.context) return false;
  const node = nodeById.get(room.sceneId);
  if (!node) return false;
  const lvl = nodeLevel(node);
  if (filter.context === "site") {
    return lvl !== 0;
  }
  if (filter.context === "structure" || filter.context === "floor") {
    if (filter.structureId && room.structureId !== filter.structureId) return true;
    if (filter.context === "floor" && filter.level != null && lvl !== filter.level) return true;
  }
  if (filter.context === "stack") {
    if (filter.structureId && room.structureId !== filter.structureId) return true;
  }
  return false;
}

export function buildSceneGraph3D(
  graph: SpatialGraph,
  route?: NavigationRoute | null,
  filter?: SceneGraphViewFilter
): SceneGraph3D {
  const laid = applySiteLayout(graph as Parameters<typeof applySiteLayout>[0]);
  const nodes = laid.nodes as MapNode[];
  const nodeById = new Map(nodes.map((n) => [n.sceneId, n]));
  const routeEdgeIds = new Set(
    route?.reachable ? route.steps.map((s) => s.exitId).filter(Boolean) : []
  );
  const routeScenes = new Set(route?.sceneIds ?? []);

  const structKinds = new Map((laid.structures ?? []).map((s) => [s.structureId, s.kind ?? "building"]));
  const rooms = nodes.map((n) => {
    const room = roomFromNode(n, structKinds);
    room.dimmed = roomDimmed(room, filter, nodeById);
    return room;
  });
  const hiddenWalls = computeHiddenWalls(nodes, laid.edges as MapEdge[]);

  const edges: EdgeSegment[] = [];
  for (const e of laid.edges as MapEdge[]) {
    const src = nodeById.get(e.sourceSceneId);
    const tgt = nodeById.get(e.targetSceneId);
    if (!src || !tgt) continue;
    const srcLvl = nodeLevel(src);
    const tgtLvl = nodeLevel(tgt);
    const vertical = srcLvl !== tgtLvl;
    const y = Math.max(floorY(srcLvl), floorY(tgtLvl)) + DOOR_HEIGHT;
    const { start, end } = edgeEndpoints(src, tgt, e);
    const from: [number, number, number] = [planToWorld(start.x, start.y)[0], y, planToWorld(start.x, start.y)[1]];
    const to: [number, number, number] = [planToWorld(end.x, end.y)[0], y, planToWorld(end.x, end.y)[1]];
    if (vertical) {
      const midX = (from[0] + to[0]) / 2;
      const midZ = (from[2] + to[2]) / 2;
      const lowY = floorY(Math.min(srcLvl, tgtLvl)) + DOOR_HEIGHT;
      const highY = floorY(Math.max(srcLvl, tgtLvl)) + DOOR_HEIGHT;
      edges.push({
        exitId: e.exitId,
        from: [midX, lowY, midZ],
        to: [midX, highY, midZ],
        onRoute: routeEdgeIds.has(e.exitId),
        vertical: true,
        label: e.label,
        targetSceneId: e.targetSceneId,
      });
    }
    const onRoute =
      routeEdgeIds.has(e.exitId) ||
      (routeScenes.has(e.sourceSceneId) && routeScenes.has(e.targetSceneId));
    edges.push({
      exitId: e.exitId,
      from: vertical
        ? ([from[0], floorY(srcLvl) + DOOR_HEIGHT, from[2]] as [number, number, number])
        : from,
      to: vertical
        ? ([to[0], floorY(tgtLvl) + DOOR_HEIGHT, to[2]] as [number, number, number])
        : to,
      onRoute,
      vertical: false,
      label: e.label,
    });
  }

  const structures: StructurePad[] = (laid.structures ?? []).map((s) => {
    const inStruct = nodes.filter((n) => n.structureId === s.structureId);
    const fp =
      structureFootprint(s.boundary) ||
      structureFootprintFromRooms(inStruct);
    let cx = 0;
    let cz = 0;
    fp.forEach(([x, z]) => {
      cx += x;
      cz += z;
    });
    if (fp.length) {
      cx /= fp.length;
      cz /= fp.length;
    }
    const containsActive = nodes.some((n) => n.structureId === s.structureId && n.isActive);
    const maxLevel = inStruct.reduce((m, n) => Math.max(m, nodeLevel(n)), 0);
    return {
      structureId: s.structureId,
      displayName: s.displayName,
      footprint: fp,
      center: [cx, 0, cz],
      kind: s.kind,
      containsActive,
      maxLevel,
      isOutdoor: s.kind === "outdoor",
    };
  });

  const references: ReferenceMarker[] = (graph.referencePoints ?? []).map((rp) => ({
    id: rp.id,
    label: rp.label,
    position: referencePointToWorld(rp.position3d),
    sceneId: rp.sceneId,
  }));

  let minX = Infinity;
  let minY = 0;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = FLOOR_HEIGHT * 3;
  let maxZ = -Infinity;

  for (const st of structures) {
    for (const [x, z] of st.footprint) {
      minX = Math.min(minX, x);
      minZ = Math.min(minZ, z);
      maxX = Math.max(maxX, x);
      maxZ = Math.max(maxZ, z);
    }
  }
  for (const r of rooms) {
    const [x, y, z] = r.position;
    const [sx, , sz] = r.size;
    minX = Math.min(minX, x - sx);
    minZ = Math.min(minZ, z - sz);
    maxX = Math.max(maxX, x + sx);
    maxY = Math.max(maxY, y + r.wallHeight + 0.5);
    maxZ = Math.max(maxZ, z + sz);
  }
  if (!Number.isFinite(minX)) {
    minX = -4;
    minZ = -4;
    maxX = 4;
    maxZ = 4;
  }

  const siteCenter: [number, number, number] = [
    (minX + maxX) / 2,
    0,
    (minZ + maxZ) / 2,
  ];

  return {
    rooms,
    edges,
    structures,
    references,
    hiddenWalls,
    siteCenter,
    bounds: { min: [minX, minY, minZ], max: [maxX, maxY, maxZ] },
  };
}
