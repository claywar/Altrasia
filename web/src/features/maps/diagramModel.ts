import type { SpatialGraph } from "../../api/client";
import type { MapEdge, MapNode, Point } from "./types";

/** Normalized plan-space point from API / layout hints (0–100). */
export function readPlanPosition(node: MapNode): Point {
  const raw = node as MapNode & {
    planPosition?: Point | { planX?: number; planY?: number; x?: number; y?: number };
  };
  const p = raw.planPosition;
  if (p && typeof p === "object") {
    const x = "planX" in p && p.planX != null ? p.planX : p.x;
    const y = "planY" in p && p.planY != null ? p.planY : p.y;
    if (x != null && y != null) return { x, y };
  }
  return { x: node.layout?.x ?? 50, y: node.layout?.y ?? 50 };
}

/** Apply plan position to layout so all renderers share one center. */
export function withPlanLayout(nodes: MapNode[]): MapNode[] {
  return nodes.map((n) => {
    const c = readPlanPosition(n);
    return { ...n, layout: { x: c.x, y: c.y } };
  });
}

export function subgraphForPlate(
  graph: SpatialGraph,
  structureId: string,
  level: number,
  levelIndex: (n: MapNode) => number
): { nodes: MapNode[]; edges: MapEdge[]; structure?: NonNullable<SpatialGraph["structures"]>[number] } {
  const mg = graph as { nodes: MapNode[]; edges: MapEdge[]; structures?: SpatialGraph["structures"] };
  const nodes = withPlanLayout(
    mg.nodes.filter((n) => n.structureId === structureId && levelIndex(n) === level)
  );
  const ids = new Set(nodes.map((n) => n.sceneId));
  const edges = (mg.edges as MapEdge[]).filter(
    (e) => ids.has(e.sourceSceneId) && ids.has(e.targetSceneId)
  );
  const structure = mg.structures?.find((s) => s.structureId === structureId);
  return { nodes, edges, structure };
}
