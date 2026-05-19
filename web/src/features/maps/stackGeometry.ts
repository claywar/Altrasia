import { computeViewBox } from "./computeViewBox";
import { readPlanPosition } from "./diagramModel";
import { plateOriginFromNodes, projectPoint } from "./diagramProjection";
import type { DiagramProjection } from "./diagramProfiles";
import { isoPlateViewBox } from "./IsoDiagramPlate";
import { isVerticalEdge, nodeLevelIndex, type StackPlate } from "./floorLevels";
import type { MapEdge, MapGraph, MapNode, Point } from "./types";

export const PLATE_GAP = 12;
export const PLATE_PAD = 5;
export const ROOT_MARGIN = 10;
const CONNECTOR_PAD = 1.5;
/** Target width in SVG units — one scale for all floors so the stack reads as one building. */
export const PLATE_TARGET_W = 132;

export function planPoint(node: MapNode): Point {
  return readPlanPosition(node);
}

export function stackPlatesDescending(plates: StackPlate[]): StackPlate[] {
  return [...plates].sort((a, b) => b.level - a.level);
}

export function verticalAnchorSceneIds(edges: MapEdge[]): Set<string> {
  const ids = new Set<string>();
  for (const e of edges) {
    if (isVerticalEdge(e)) {
      ids.add(e.sourceSceneId);
      ids.add(e.targetSceneId);
    }
  }
  return ids;
}

export function computeStackAnchorX(nodes: MapNode[], anchorIds: Set<string>): number {
  const pts = nodes.filter((n) => anchorIds.has(n.sceneId)).map(planPoint);
  if (pts.length === 0) return 50;
  return pts.reduce((s, p) => s + p.x, 0) / pts.length;
}

export function normalizePlateNodes(
  plate: StackPlate,
  stackAnchorX: number,
  anchorIds: Set<string>
): MapNode[] {
  const anchorOnPlate = plate.nodes.filter((n) => anchorIds.has(n.sceneId));
  if (anchorOnPlate.length === 0) return plate.nodes;
  const avgX =
    anchorOnPlate.reduce((s, n) => s + planPoint(n).x, 0) / anchorOnPlate.length;
  const dx = stackAnchorX - avgX;
  if (Math.abs(dx) < 0.01) return plate.nodes;
  return plate.nodes.map((n) => {
    const pp = planPoint(n);
    return {
      ...n,
      layout: { x: (n.layout?.x ?? pp.x) + dx, y: n.layout?.y ?? pp.y },
      planPosition: { x: pp.x + dx, y: pp.y },
    };
  });
}

function plateViewBoxFromNodes(nodes: MapNode[], projection: DiagramProjection) {
  if (projection === "iso") {
    return isoPlateViewBox(nodes, PLATE_PAD);
  }
  const sub: MapGraph = { activeSceneId: "", nodes, edges: [] };
  const vb = computeViewBox(sub, "full");
  return {
    x: vb.x - PLATE_PAD,
    y: vb.y - PLATE_PAD,
    w: vb.w + PLATE_PAD * 2,
    h: vb.h + PLATE_PAD * 2,
  };
}

export type PlateLayoutMetrics = {
  plate: StackPlate;
  level: number;
  label: string;
  nodes: MapNode[];
  vb: { x: number; y: number; w: number; h: number };
  y: number;
  scale: number;
  scaledW: number;
  scaledH: number;
};

export type StackLayoutResult = {
  layouts: PlateLayoutMetrics[];
  totalH: number;
  maxW: number;
  rootW: number;
  rootH: number;
};

export function layoutStackPlates(
  plates: StackPlate[],
  verticalEdges: MapEdge[],
  projection: DiagramProjection = "iso"
): StackLayoutResult {
  const ordered = stackPlatesDescending(plates);
  const anchorIds = verticalAnchorSceneIds(verticalEdges);
  const allNodes = plates.flatMap((p) => p.nodes);
  const stackAnchorX = computeStackAnchorX(allNodes, anchorIds);

  const layouts: PlateLayoutMetrics[] = [];

  for (const plate of ordered) {
    const nodes = normalizePlateNodes(plate, stackAnchorX, anchorIds);
    const vb = plateViewBoxFromNodes(nodes, projection);
    layouts.push({
      plate,
      level: plate.level,
      label: plate.label,
      nodes,
      vb,
      y: 0,
      scale: 1,
      scaledW: vb.w,
      scaledH: vb.h,
    });
  }

  const maxVbW = Math.max(...layouts.map((l) => l.vb.w), 8);
  const unifiedScale = PLATE_TARGET_W / maxVbW;

  let yCursor = 0;
  for (const layout of layouts) {
    layout.scale = unifiedScale;
    layout.scaledW = layout.vb.w * unifiedScale;
    layout.scaledH = layout.vb.h * unifiedScale;
    layout.y = yCursor;
    yCursor += layout.scaledH + PLATE_GAP;
  }

  const totalH = layouts.length > 0 ? yCursor - PLATE_GAP : 0;
  const labelGutter = 14;
  const rootH = totalH + ROOT_MARGIN * 2;
  const rootW = PLATE_TARGET_W + ROOT_MARGIN * 2 + labelGutter;
  return { layouts, totalH, maxW: PLATE_TARGET_W, rootW, rootH };
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

/** Map plan point on a plate into root stack SVG coordinates. */
export function planToStackSvg(
  layout: PlateLayoutMetrics,
  planX: number,
  planY: number,
  projection: DiagramProjection = "iso"
): Point {
  const origin = plateOriginFromNodes(layout.nodes);
  const display =
    projection === "iso"
      ? projectPoint({ x: planX, y: planY }, "iso", origin)
      : { x: planX, y: planY };
  const localX = (display.x - layout.vb.x) * layout.scale;
  const localY = (display.y - layout.vb.y) * layout.scale;
  const labelGutter = 14;
  return {
    x: ROOT_MARGIN + labelGutter + localX,
    y: ROOT_MARGIN + layout.y + localY,
  };
}

function pickVerticalAnchorNode(
  edge: MapEdge,
  loLayout: PlateLayoutMetrics
): MapNode | undefined {
  return (
    loLayout.nodes.find((n) => n.sceneId === edge.sourceSceneId) ??
    loLayout.nodes.find((n) => n.sceneId === edge.targetSceneId)
  );
}

export function stackConnectors(
  layouts: PlateLayoutMetrics[],
  verticalEdges: MapEdge[],
  nodeById: Map<string, MapNode>,
  projection: DiagramProjection = "iso"
): StackConnector[] {
  const levelToLayout = new Map(layouts.map((l) => [l.level, l]));
  const seen = new Set<string>();
  const connectors: StackConnector[] = [];

  for (const edge of verticalEdges) {
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

    const loLayout = levelToLayout.get(loLvl);
    const hiLayout = levelToLayout.get(hiLvl);
    if (!loLayout || !hiLayout) continue;

    const anchorNode = pickVerticalAnchorNode(edge, loLayout);
    if (!anchorNode) continue;

    const pp = planPoint(anchorNode);
    const top = planToStackSvg(loLayout, pp.x, pp.y, projection);
    const ax = top.x;
    const y1 = ROOT_MARGIN + loLayout.y + loLayout.scaledH + CONNECTOR_PAD;
    const y2 = ROOT_MARGIN + hiLayout.y - CONNECTOR_PAD;
    const up = tgtLvl > srcLvl;

    connectors.push({
      edge,
      x1: ax,
      y1,
      x2: ax,
      y2,
      label: connectorLabel(edge, srcLvl, tgtLvl),
      kind: (edge.kind ?? "stairs").toLowerCase(),
      direction: up ? "up" : "down",
    });
  }
  return connectors;
}

export function levelSelectorBadge(level: number): string {
  if (level > 0) return `+${level}`;
  if (level === 0) return "G";
  if (level === -1) return "B1";
  return `${level}`;
}

export function levelSelectorIcon(level: number): "ladder" | "stairs" | "floor" {
  if (level < 0) return "ladder";
  if (level > 0) return "stairs";
  return "floor";
}

export function plateDescription(nodes: MapNode[]): string {
  const active = nodes.find((n) => n.isActive);
  const pick = active ?? nodes[0];
  const n = pick as MapNode & { locationDescription?: string };
  if (n?.locationDescription) return n.locationDescription;
  if (nodes.length === 1) return nodes[0]!.locationName;
  return nodes.map((x) => x.locationName).join(", ");
}
