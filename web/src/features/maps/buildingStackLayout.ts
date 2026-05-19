import { readPlanPosition } from "./diagramModel";
import {
  boundsFromProjectedFootprints,
  plateOriginFromNodes,
  projectFootprint,
  structureIsoFloorPath,
} from "./diagramProjection";
import { planToIso, isoBoundsFromCorners, isoPointsToPath } from "./isoProjection";
import { nodeFootprint } from "./layoutGeometry";
import { isVerticalEdge, nodeLevelIndex, type StackPlate } from "./floorLevels";
import { stackPlatesDescending } from "./stackGeometry";
import type { MapEdge, MapNode, MapStructure, Point } from "./types";

// Re-export for tests — isoProjection does not export WALL_RISE
const SLAB_RISE = 2.8;
const FLOOR_GAP = 10;
export const ROOT_MARGIN = 12;
export const LABEL_GUTTER = 16;
export const BUILDING_TARGET_W = 160;

export type UnifiedFloorLayout = {
  plate: StackPlate;
  level: number;
  label: string;
  nodes: MapNode[];
  edges: MapEdge[];
  /** Vertical offset of this floor slab in stack SVG space */
  stackY: number;
};

export type UnifiedStackLayout = {
  origin: Point;
  vb: { x: number; y: number; w: number; h: number };
  scale: number;
  floorStep: number;
  slabDepth: number;
  shellPath: string | null;
  floors: UnifiedFloorLayout[];
  totalStackH: number;
  rootW: number;
  rootH: number;
};

type StructureBoundary = MapStructure["boundary"];

function boundaryCentroid(boundary: StructureBoundary | undefined): Point | null {
  if (!boundary) return null;
  if (boundary.vertices && boundary.vertices.length >= 3) {
    const v = boundary.vertices;
    return {
      x: v.reduce((s, p) => s + p.x, 0) / v.length,
      y: v.reduce((s, p) => s + p.y, 0) / v.length,
    };
  }
  if (boundary.cx != null && boundary.cy != null) return { x: boundary.cx, y: boundary.cy };
  if (boundary.x != null && boundary.y != null && boundary.w != null && boundary.h != null) {
    return { x: boundary.x + boundary.w / 2, y: boundary.y + boundary.h / 2 };
  }
  return null;
}

/** One plan origin for every floor — structure placement or shell centroid. */
export function structureStackOrigin(
  structure: MapStructure | undefined,
  allNodes: MapNode[],
  worldOrigin?: Point
): Point {
  if (worldOrigin) return worldOrigin;
  const fromBoundary = boundaryCentroid(structure?.boundary);
  if (fromBoundary) return fromBoundary;
  return plateOriginFromNodes(allNodes);
}

function shellIsoBounds(shellPath: string | null, origin: Point, boundary: StructureBoundary | undefined) {
  if (boundary?.vertices && boundary.vertices.length >= 3) {
    const corners = boundary.vertices.flatMap((v) => {
      const base = planToIso(v.x, v.y, origin);
      return [base, { x: base.x, y: base.y - SLAB_RISE }];
    });
    return isoBoundsFromCorners(corners);
  }
  if (shellPath) {
    return { minX: -40, minY: -30, maxX: 40, maxY: 30 };
  }
  return null;
}

function unifiedViewBox(
  structure: MapStructure | undefined,
  allNodes: MapNode[],
  origin: Point,
  pad = 6
) {
  const projected = allNodes.map((n) => ({
    ...projectFootprint(nodeFootprint(n), "iso", origin),
  }));
  const roomBounds = boundsFromProjectedFootprints(projected, pad);
  const boundary = structure?.boundary ?? undefined;
  const shellBounds = shellIsoBounds(
    structureIsoFloorPath(boundary, origin),
    origin,
    boundary
  );

  let minX = roomBounds.x;
  let minY = roomBounds.y;
  let maxX = roomBounds.x + roomBounds.w;
  let maxY = roomBounds.y + roomBounds.h;

  if (shellBounds) {
    minX = Math.min(minX, shellBounds.minX - pad);
    minY = Math.min(minY, shellBounds.minY - pad);
    maxX = Math.max(maxX, shellBounds.maxX + pad);
    maxY = Math.max(maxY, shellBounds.maxY + pad);
  }

  return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
}

export function layoutUnifiedBuildingStack(
  plates: StackPlate[],
  structure: MapStructure | undefined,
  _verticalEdges: MapEdge[],
  worldOrigin?: Point
): UnifiedStackLayout | null {
  if (plates.length === 0) return null;

  const ordered = stackPlatesDescending(plates);
  const allNodes = ordered.flatMap((p) => p.nodes);
  const origin = structureStackOrigin(structure, allNodes, worldOrigin);
  const boundary = structure?.boundary ?? undefined;
  const vb = unifiedViewBox(structure, allNodes, origin);
  const shellPath = structureIsoFloorPath(boundary, origin);
  const slabDepth = vb.h * 0.55 + SLAB_RISE;
  const floorStep = slabDepth + FLOOR_GAP;

  const floors: UnifiedFloorLayout[] = ordered.map((plate, index) => ({
    plate,
    level: plate.level,
    label: plate.label,
    nodes: plate.nodes,
    edges: plate.edges,
    stackY: index * floorStep,
  }));

  const totalStackH =
    floors.length > 0 ? floors[floors.length - 1]!.stackY + slabDepth : slabDepth;
  const scale = BUILDING_TARGET_W / Math.max(vb.w, 8);
  const scaledW = vb.w * scale;
  const scaledStackH = totalStackH * scale;
  const rootW = scaledW + ROOT_MARGIN * 2 + LABEL_GUTTER;
  const rootH = scaledStackH + ROOT_MARGIN * 2;

  return {
    origin,
    vb,
    scale,
    floorStep,
    slabDepth,
    shellPath,
    floors,
    totalStackH,
    rootW,
    rootH,
  };
}

/** Plan position → root stack SVG coordinates (shared origin + viewBox). */
export function planToUnifiedStack(
  layout: UnifiedStackLayout,
  planX: number,
  planY: number,
  floorStackY: number
): Point {
  const iso = planToIso(planX, planY, layout.origin);
  const localX = (iso.x - layout.vb.x) * layout.scale;
  const localY = (iso.y - layout.vb.y) * layout.scale + floorStackY * layout.scale;
  return {
    x: ROOT_MARGIN + LABEL_GUTTER + localX,
    y: ROOT_MARGIN + localY,
  };
}

export type StackConnector = {
  edge: MapEdge;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  label: string;
  kind: string;
  direction: "up" | "down";
};

export function connectorLabel(edge: MapEdge, srcLvl: number, tgtLvl: number): string {
  const kind = (edge.kind ?? "stairs").toLowerCase();
  const up = tgtLvl > srcLvl;
  if (kind === "ladder") return up ? "LADDER UP" : "LADDER DOWN";
  return up ? "STAIRS UP" : "STAIRS DOWN";
}

function planPoint(node: MapNode): Point {
  return readPlanPosition(node);
}

export function unifiedStackConnectors(
  layout: UnifiedStackLayout,
  verticalEdges: MapEdge[],
  nodeById: Map<string, MapNode>
): StackConnector[] {
  const levelToFloor = new Map(layout.floors.map((f) => [f.level, f]));
  const seen = new Set<string>();
  const connectors: StackConnector[] = [];
  const slabScaled = layout.slabDepth * layout.scale;

  for (const edge of verticalEdges) {
    if (!isVerticalEdge(edge)) continue;
    const src = nodeById.get(edge.sourceSceneId);
    const tgt = nodeById.get(edge.targetSceneId);
    if (!src || !tgt) continue;

    const srcLvl = nodeLevelIndex(src);
    const tgtLvl = nodeLevelIndex(tgt);
    if (srcLvl === tgtLvl) continue;

    const loLvl = Math.min(srcLvl, tgtLvl);
    const hiLvl = Math.max(srcLvl, tgtLvl);
    const pairKey = `${loLvl}:${hiLvl}:${edge.kind ?? "stairs"}`;
    if (seen.has(pairKey)) continue;
    seen.add(pairKey);

    const loFloor = levelToFloor.get(loLvl);
    const hiFloor = levelToFloor.get(hiLvl);
    if (!loFloor || !hiFloor) continue;

    const anchor = loFloor.nodes.find((n) => n.sceneId === edge.sourceSceneId || n.sceneId === edge.targetSceneId);
    if (!anchor) continue;

    const pp = planPoint(anchor);
    const pt = planToUnifiedStack(layout, pp.x, pp.y, loFloor.stackY);
    const hiPt = planToUnifiedStack(layout, pp.x, pp.y, hiFloor.stackY);
    const up = tgtLvl > srcLvl;

    connectors.push({
      edge,
      x1: pt.x,
      y1: pt.y + slabScaled * 0.85,
      x2: hiPt.x,
      y2: hiPt.y + slabScaled * 0.15,
      label: connectorLabel(edge, srcLvl, tgtLvl),
      kind: (edge.kind ?? "stairs").toLowerCase(),
      direction: up ? "up" : "down",
    });
  }
  return connectors;
}

/** Side faces linking top and bottom floor slabs (one building volume). */
export function buildingExtrusionFaces(
  layout: UnifiedStackLayout,
  structure: MapStructure | undefined
): string[] {
  const boundary = structure?.boundary;
  if (!boundary?.vertices || boundary.vertices.length < 3) return [];

  const verts = boundary.vertices;
  const bottomY = layout.floors[layout.floors.length - 1]!.stackY * layout.scale + ROOT_MARGIN;
  const topY = ROOT_MARGIN;
  const faces: string[] = [];

  for (let i = 0; i < verts.length; i++) {
    const v0 = verts[i]!;
    const v1 = verts[(i + 1) % verts.length]!;
    const b0 = planToIso(v0.x, v0.y, layout.origin);
    const b1 = planToIso(v1.x, v1.y, layout.origin);
    const t0 = {
      x: (b0.x - layout.vb.x) * layout.scale + ROOT_MARGIN + LABEL_GUTTER,
      y: (b0.y - layout.vb.y) * layout.scale + topY,
    };
    const t1 = {
      x: (b1.x - layout.vb.x) * layout.scale + ROOT_MARGIN + LABEL_GUTTER,
      y: (b1.y - layout.vb.y) * layout.scale + topY,
    };
    const bot0 = { ...t0, y: (b0.y - layout.vb.y) * layout.scale + bottomY + layout.slabDepth * layout.scale };
    const bot1 = { ...t1, y: (b1.y - layout.vb.y) * layout.scale + bottomY + layout.slabDepth * layout.scale };
    faces.push(isoPointsToPath([t0, t1, bot1, bot0]));
  }
  return faces;
}
