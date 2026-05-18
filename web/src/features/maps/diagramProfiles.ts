import type { MapViewMode } from "./floorLevels";

/** How each surface renders the same spatial-graph definitions. */
export type DiagramProjection = "plan" | "iso";

export type DiagramProfile = {
  projection: DiagramProjection;
  showEdges: boolean;
  showEnvelopes: boolean;
  showGhosts: boolean;
  showUnderlay: boolean;
  compact: boolean;
};

export const DIAGRAM_PROFILES: Record<MapViewMode, DiagramProfile> = {
  site: {
    projection: "plan",
    showEdges: true,
    showEnvelopes: true,
    showGhosts: false,
    showUnderlay: true,
    compact: false,
  },
  structure: {
    projection: "plan",
    showEdges: true,
    showEnvelopes: true,
    showGhosts: true,
    showUnderlay: false,
    compact: false,
  },
  floor: {
    projection: "plan",
    showEdges: true,
    showEnvelopes: true,
    showGhosts: false,
    showUnderlay: false,
    compact: false,
  },
  stack: {
    projection: "iso",
    showEdges: true,
    showEnvelopes: true,
    showGhosts: false,
    showUnderlay: false,
    compact: true,
  },
};
