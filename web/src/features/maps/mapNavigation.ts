import type { SpatialGraph } from "../../api/client";

export type MapDestination = {
  exitId: string;
  label: string;
  targetSceneId: string;
  targetName: string;
  direction?: string;
  travelSteps?: number;
  kind?: string;
  doorState?: string;
};

const DIR_GLYPH: Record<string, string> = {
  N: "↑",
  NE: "↗",
  E: "→",
  SE: "↘",
  S: "↓",
  SW: "↙",
  W: "←",
  NW: "↖",
};

export function directionGlyph(direction?: string): string {
  if (!direction) return "→";
  return DIR_GLYPH[direction] ?? "→";
}

/** Exits leading out from the persona's current scene. */
export function destinationsFromActive(graph: SpatialGraph): MapDestination[] {
  const activeId = graph.activeSceneId;
  const nodeById = new Map(graph.nodes.map((n) => [n.sceneId, n]));
  return graph.edges
    .filter((e) => e.sourceSceneId === activeId)
    .map((e) => {
      const target = nodeById.get(e.targetSceneId);
      return {
        exitId: e.exitId,
        label: e.label,
        targetSceneId: e.targetSceneId,
        targetName: target?.locationName ?? e.label,
        direction: e.direction,
        travelSteps: e.travelSteps,
        kind: e.kind,
        doorState: e.doorState,
      };
    });
}

import {
  activeStructureId,
  levelsForStructure,
  levelLabelFor,
  nodeLevelIndex,
  personaOffSitePlan,
  type MapViewMode,
} from "./floorLevels";
import type { MapGraph } from "./types";

export type MapViewCapabilities = {
  hasMultipleFloors: boolean;
  floorCount: number;
  floorLabels: string[];
  personaOffSitePlan: boolean;
  personaLevelLabel: string | null;
  recommendedModes: MapViewMode[];
};

export function mapViewCapabilities(graph: SpatialGraph | null): MapViewCapabilities {
  if (!graph) {
    return {
      hasMultipleFloors: false,
      floorCount: 1,
      floorLabels: [],
      personaOffSitePlan: false,
      personaLevelLabel: null,
      recommendedModes: [],
    };
  }
  const mg = graph as MapGraph;
  const structId = activeStructureId(mg);
  const active = mg.nodes.find((n) => n.isActive);
  const levels = structId ? levelsForStructure(mg.nodes, structId) : [];
  const offPlan = personaOffSitePlan(mg);
  const recommended: MapViewMode[] = [];
  if (offPlan) {
    recommended.push("stack", "floor");
  } else if (levels.length > 1) {
    recommended.push("stack");
  }
  if (structId && levels.length > 1) {
    recommended.push("structure");
  }
  const personaLevelLabel =
    active && structId
      ? levelLabelFor(mg.nodes, structId, nodeLevelIndex(active))
      : active?.mapZone ?? null;

  return {
    hasMultipleFloors: levels.length > 1,
    floorCount: levels.length,
    floorLabels: levels.map((l) =>
      structId ? levelLabelFor(mg.nodes, structId, l) : `Level ${l}`
    ),
    personaOffSitePlan: offPlan,
    personaLevelLabel,
    recommendedModes: [...new Set(recommended)],
  };
}

export function viewModeDescription(
  mode: MapViewMode,
  caps: MapViewCapabilities
): { title: string; subtitle: string } {
  switch (mode) {
    case "site":
      return {
        title: "Site",
        subtitle: caps.personaOffSitePlan
          ? "Ground floors only — you are on another level"
          : "All buildings · ground floor",
      };
    case "structure":
      return {
        title: "Structure",
        subtitle: caps.hasMultipleFloors
          ? `One building · ${caps.floorCount} floors`
          : "One building · single floor",
      };
    case "floor":
      return {
        title: "Floor",
        subtitle: caps.personaLevelLabel
          ? `Your level · ${caps.personaLevelLabel}`
          : "One floor · room layout",
      };
    case "stack":
      return {
        title: "Stack",
        subtitle: caps.hasMultipleFloors
          ? `${caps.floorCount} floors stacked`
          : "Vertical floors",
      };
  }
}

const BLOCKED_DOORS = new Set(["locked", "sealed", "blocked"]);

function isTraversable(edge: SpatialGraph["edges"][0]): boolean {
  const state = (edge.doorState ?? "").toLowerCase();
  return !BLOCKED_DOORS.has(state);
}

/** All scenes reachable from active via exit graph (BFS, bidirectional). */
export function reachableSceneIdsFromGraph(
  graph: SpatialGraph,
  fromSceneId: string = graph.activeSceneId
): Set<string> {
  const adj = new Map<string, Set<string>>();
  for (const e of graph.edges) {
    if (!isTraversable(e)) continue;
    if (!adj.has(e.sourceSceneId)) adj.set(e.sourceSceneId, new Set());
    if (!adj.has(e.targetSceneId)) adj.set(e.targetSceneId, new Set());
    adj.get(e.sourceSceneId)!.add(e.targetSceneId);
    adj.get(e.targetSceneId)!.add(e.sourceSceneId);
  }
  const seen = new Set<string>();
  const queue = [fromSceneId];
  while (queue.length) {
    const cur = queue.shift()!;
    for (const nxt of adj.get(cur) ?? []) {
      if (nxt !== fromSceneId && !seen.has(nxt)) {
        seen.add(nxt);
        queue.push(nxt);
      }
    }
  }
  return seen;
}

/** Direct neighbors only (1-hop). */
export function reachableSceneIds(graph: SpatialGraph): Set<string> {
  return reachableSceneIdsFromGraph(graph, graph.activeSceneId);
}

/** True when two scenes share a traversable exit edge. */
export function areAdjacentScenes(
  graph: SpatialGraph,
  fromSceneId: string,
  toSceneId: string
): boolean {
  if (fromSceneId === toSceneId) return false;
  return graph.edges.some(
    (e) =>
      isTraversable(e) &&
      ((e.sourceSceneId === fromSceneId && e.targetSceneId === toSceneId) ||
        (e.sourceSceneId === toSceneId && e.targetSceneId === fromSceneId))
  );
}

/** Compass hint from the first outbound exit direction at the active scene. */
export function compassFromActive(graph: SpatialGraph): string | null {
  const edge = graph.edges.find((e) => e.sourceSceneId === graph.activeSceneId && e.direction);
  if (!edge?.direction) return null;
  return directionGlyph(edge.direction);
}
