import { footprintBounds, neighborSceneIds, nodeFootprint, structureEnvelope } from "./layoutGeometry";
import type { MapGraph } from "./types";

export type ViewBox = { x: number; y: number; w: number; h: number };

const PAD_NEIGHBORHOOD = 6;
const PAD_FULL = 11;
const TITLE_HEADROOM = 4;

function expandBbox(
  bbox: ViewBox | null,
  minX: number,
  minY: number,
  maxX: number,
  maxY: number
): ViewBox {
  if (!bbox) return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
  return {
    x: Math.min(bbox.x, minX),
    y: Math.min(bbox.y, minY),
    w: Math.max(bbox.x + bbox.w, maxX) - Math.min(bbox.x, minX),
    h: Math.max(bbox.y + bbox.h, maxY) - Math.min(bbox.y, minY),
  };
}

export type ViewFitMode = "neighborhood" | "full";

export function computeViewBox(
  graph: MapGraph,
  mode: ViewFitMode = "neighborhood"
): ViewBox {
  const active = graph.nodes.find((n) => n.isActive);
  const focusId = active?.sceneId;
  const includeIds =
    mode === "full" || !focusId
      ? new Set(graph.nodes.map((n) => n.sceneId))
      : neighborSceneIds(graph, focusId, 2);

  const nodes = graph.nodes.filter((n) => includeIds.has(n.sceneId));
  let bbox: ViewBox | null = null;

  for (const n of nodes) {
    const b = footprintBounds(nodeFootprint(n), 1);
    bbox = expandBbox(bbox, b.minX, b.minY, b.maxX, b.maxY);
  }

  for (const st of graph.structures ?? []) {
    const env = structureEnvelope(st.structureId, graph.nodes, st.boundary);
    if (!env) continue;
    const hasNode = nodes.some((n) => n.structureId === st.structureId);
    if (mode === "neighborhood" && !hasNode) continue;
    bbox = expandBbox(bbox, env.minX, env.minY, env.maxX, env.maxY);
  }

  if (!bbox) return { x: 0, y: 0, w: 100, h: 100 };

  const pad = mode === "full" ? PAD_FULL : PAD_NEIGHBORHOOD;
  return {
    x: bbox.x - pad,
    y: bbox.y - pad - TITLE_HEADROOM,
    w: bbox.w + pad * 2,
    h: bbox.h + pad * 2 + TITLE_HEADROOM,
  };
}

export function filterGraphForView(graph: MapGraph, mode: ViewFitMode): MapGraph {
  if (mode === "full") return graph;
  const active = graph.nodes.find((n) => n.isActive);
  if (!active) return graph;
  const ids = neighborSceneIds(graph, active.sceneId, 2);
  return {
    ...graph,
    nodes: graph.nodes.filter((n) => ids.has(n.sceneId)),
    edges: graph.edges.filter(
      (e) => ids.has(e.sourceSceneId) && ids.has(e.targetSceneId)
    ),
  };
}
