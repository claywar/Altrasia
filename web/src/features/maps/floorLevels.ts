import { readPlanPosition } from "./diagramModel";
import { applySiteLayout } from "./worldSiteLayout";
import type { MapEdge, MapGraph, MapNode } from "./types";

export type MapViewMode = "site" | "structure" | "floor" | "stack";

/** Site-scale plans show ground floor per building (reference WF-14). */
export const SITE_DISPLAY_LEVEL = 0;

export function nodeLevelIndex(node: MapNode): number {
  if (node.levelIndex != null) return node.levelIndex;
  const ml = (node as MapNode & { mapLevel?: number }).mapLevel;
  return ml ?? 0;
}

export function levelsForStructure(nodes: MapNode[], structureId: string): number[] {
  const levels = new Set<number>();
  for (const n of nodes) {
    if (n.structureId === structureId) levels.add(nodeLevelIndex(n));
  }
  return [...levels].sort((a, b) => a - b);
}

export function levelLabelFor(nodes: MapNode[], structureId: string, level: number): string {
  const hit = nodes.find(
    (n) => n.structureId === structureId && nodeLevelIndex(n) === level
  );
  if (hit?.levelLabel) return hit.levelLabel;
  if (hit?.mapZone) return hit.mapZone;
  if (level === 0) return "Ground floor";
  if (level > 0) return `Level +${level}`;
  return `Level ${level}`;
}

export function activeStructureId(graph: MapGraph): string | undefined {
  return graph.nodes.find((n) => n.isActive)?.structureId;
}

export function activeLevel(graph: MapGraph): number {
  const active = graph.nodes.find((n) => n.isActive);
  return active ? nodeLevelIndex(active) : 0;
}

export function activeSceneNode(graph: MapGraph): MapNode | undefined {
  return graph.nodes.find((n) => n.isActive);
}

/** Default map overlay mode from active scene context (MAP-16). */
export function defaultViewModeForGraph(graph: MapGraph): MapViewMode {
  const active = activeSceneNode(graph);
  if (!active?.structureId) return "site";
  const structKind = graph.structures?.find((s) => s.structureId === active.structureId)?.kind;
  if (structKind === "outdoor") return "site";
  const levels = levelsForStructure(graph.nodes, active.structureId);
  if (levels.length > 1) return "stack";
  return "floor";
}

export function isVerticalEdge(edge: MapEdge): boolean {
  const k = edge.kind?.toLowerCase();
  return k === "stairs" || k === "ladder" || k === "elevator" || k === "shaft";
}

/** Which floor a structure draws at site scale (always ground). */
export function siteStructureLevel(_structureId?: string): number {
  return SITE_DISPLAY_LEVEL;
}

/** Persona is on a floor not shown on the site plan. */
export function personaOffSitePlan(graph: MapGraph): boolean {
  const active = activeSceneNode(graph);
  if (!active?.structureId) return false;
  return nodeLevelIndex(active) !== siteStructureLevel(active.structureId);
}

export type PreparedMapView = {
  graph: MapGraph;
  focusStructureId?: string;
  focusLevel: number;
  /** Active scene not on the visible plan — show marker on structure shell. */
  offPlanActive?: MapNode;
};

function filterNodesForLevel(
  nodes: MapNode[],
  levelForStructure: (structureId: string | undefined) => number
): MapNode[] {
  return nodes.filter((n) => {
    if (!n.structureId) return true;
    return nodeLevelIndex(n) === levelForStructure(n.structureId);
  });
}

function filterEdges(nodes: MapNode[], edges: MapEdge[]): MapEdge[] {
  const visible = new Set(nodes.map((n) => n.sceneId));
  return edges.filter(
    (e) =>
      !isVerticalEdge(e) &&
      visible.has(e.sourceSceneId) &&
      visible.has(e.targetSceneId)
  );
}

/** Slice graph for a view mode — never stacks floors on one plan. */
export function prepareGraphForView(
  graph: MapGraph,
  mode: MapViewMode,
  options?: { selectedLevel?: number }
): PreparedMapView {
  const focusStructureId = activeStructureId(graph);
  const active = activeSceneNode(graph);
  const personaLevel = active ? nodeLevelIndex(active) : SITE_DISPLAY_LEVEL;

  if (mode === "stack") {
    return { graph, focusStructureId, focusLevel: personaLevel };
  }

  if (mode === "floor" && focusStructureId) {
    const focusLevel = options?.selectedLevel ?? personaLevel;
    const nodes = graph.nodes.filter(
      (n) =>
        n.structureId === focusStructureId && nodeLevelIndex(n) === focusLevel
    );
    return {
      graph: {
        ...graph,
        nodes,
        edges: filterEdges(nodes, graph.edges as MapEdge[]),
        structures: graph.structures?.filter((s) => s.structureId === focusStructureId),
      },
      focusStructureId,
      focusLevel,
    };
  }

  if (mode === "structure" && focusStructureId) {
    const focusLevel = options?.selectedLevel ?? personaLevel;
    const primary = filterNodesForLevel(graph.nodes, (sid) =>
      sid === focusStructureId ? focusLevel : siteStructureLevel(sid)
    );
    const levels = levelsForStructure(graph.nodes, focusStructureId);
    const ghostNodes: MapNode[] =
      levels.length > 1
        ? graph.nodes
            .filter(
              (n) =>
                n.structureId === focusStructureId &&
                nodeLevelIndex(n) !== focusLevel
            )
            .map((n) => {
              const c = readPlanPosition(n);
              return {
                ...n,
                layout: { x: c.x, y: c.y },
                isActive: false,
                ghost: true,
              };
            })
        : [];
    const nodes = [...primary, ...ghostNodes];
    const offPlanActive =
      active &&
      active.structureId === focusStructureId &&
      nodeLevelIndex(active) !== focusLevel
        ? active
        : undefined;
    return {
      graph: {
        ...graph,
        nodes,
        edges: filterEdges(nodes, graph.edges as MapEdge[]),
        structures: graph.structures,
      },
      focusStructureId,
      focusLevel,
      offPlanActive,
    };
  }

  // Site: every building at ground floor; persona may be elsewhere (badge only).
  const nodes = filterNodesForLevel(graph.nodes, (sid) => siteStructureLevel(sid));
  const offPlanActive =
    active?.structureId && nodeLevelIndex(active) !== siteStructureLevel(active.structureId)
      ? active
      : undefined;

  const siteGraph = applySiteLayout({
    ...graph,
    nodes,
    edges: filterEdges(nodes, graph.edges as MapEdge[]),
  });

  return {
    graph: siteGraph,
    focusStructureId,
    focusLevel: SITE_DISPLAY_LEVEL,
    offPlanActive,
  };
}

export type StackPlate = {
  level: number;
  label: string;
  nodes: MapNode[];
  edges: MapEdge[];
};

export function stackPlatesForStructure(graph: MapGraph, structureId: string): StackPlate[] {
  const levels = levelsForStructure(graph.nodes, structureId);
  return levels.map((level) => {
    const nodes = graph.nodes.filter(
      (n) => n.structureId === structureId && nodeLevelIndex(n) === level
    );
    const ids = new Set(nodes.map((n) => n.sceneId));
    const edges = (graph.edges as MapEdge[]).filter(
      (e) =>
        !isVerticalEdge(e) &&
        ids.has(e.sourceSceneId) &&
        ids.has(e.targetSceneId)
    );
    return {
      level,
      label: levelLabelFor(graph.nodes, structureId, level),
      nodes,
      edges,
    };
  });
}

export function verticalLinksForStructure(
  graph: MapGraph,
  structureId: string
): MapEdge[] {
  const ids = new Set(
    graph.nodes.filter((n) => n.structureId === structureId).map((n) => n.sceneId)
  );
  return (graph.edges as MapEdge[]).filter(
    (e) =>
      isVerticalEdge(e) && ids.has(e.sourceSceneId) && ids.has(e.targetSceneId)
  );
}
