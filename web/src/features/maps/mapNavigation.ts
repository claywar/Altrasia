import type { SpatialGraph } from "../../api/client";

export type MapDestination = {
  exitId: string;
  label: string;
  targetSceneId: string;
  targetName: string;
  direction?: string;
  travelSteps?: number;
  kind?: string;
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

export function reachableSceneIds(graph: SpatialGraph): Set<string> {
  return new Set(
    graph.edges
      .filter((e) => e.sourceSceneId === graph.activeSceneId)
      .map((e) => e.targetSceneId)
  );
}
