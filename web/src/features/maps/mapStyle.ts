import type { SpatialGraph } from "../../api/client";

export type ArchitectureStyle = "diagram" | "blueprint" | "minimal";

export function resolveArchitectureStyle(graph: SpatialGraph | null): ArchitectureStyle {
  const raw = graph?.layout?.architectureStyle;
  if (raw === "blueprint" || raw === "minimal" || raw === "diagram") return raw;
  return "diagram";
}

export type MapStyleTokens = {
  roomFill: string;
  roomFillActive: string;
  roomStroke: string;
  roomStrokeWidth: number;
  envelopeStroke: string;
  envelopeStrokeWidth: number;
  envelopeDasharray: string | undefined;
  doubleWall: boolean;
  showStructureFill: boolean;
  structureFill: string;
  structureFillActive: string;
  structureFillOther: string;
  labelFont: string;
  roomFillOpacity: number;
  corridorFill: string;
};

export function styleTokens(
  style: ArchitectureStyle,
  activeStructure: boolean
): MapStyleTokens {
  if (style === "minimal") {
    return {
      roomFill: "none",
      roomFillActive: "none",
      roomStroke: "var(--map-wall, var(--border))",
      roomStrokeWidth: 0.6,
      envelopeStroke: "var(--map-wall, var(--border))",
      envelopeStrokeWidth: 0.8,
      envelopeDasharray: "4 2",
      doubleWall: false,
      showStructureFill: false,
      structureFill: "none",
      structureFillActive: "none",
      structureFillOther: "none",
      labelFont: "var(--font-sans, system-ui, sans-serif)",
      roomFillOpacity: 1,
      corridorFill: "var(--map-corridor-fill, rgba(80, 90, 110, 0.2))",
    };
  }
  if (style === "blueprint") {
    return {
      roomFill: "var(--map-room-fill, rgba(100, 110, 130, 0.18))",
      roomFillActive: "var(--accent)",
      roomStroke: "var(--map-wall, var(--border))",
      roomStrokeWidth: 0.55,
      envelopeStroke: "var(--map-wall, var(--border))",
      envelopeStrokeWidth: 0.9,
      envelopeDasharray: undefined,
      doubleWall: true,
      showStructureFill: true,
      structureFill: activeStructure
        ? "var(--map-structure-active-fill, rgba(100, 130, 180, 0.22))"
        : "var(--map-structure-fill, rgba(120, 130, 150, 0.12))",
      structureFillActive: "var(--map-structure-active-fill, rgba(100, 130, 180, 0.22))",
      structureFillOther: "var(--map-structure-fill, rgba(120, 130, 150, 0.08))",
      labelFont: "var(--font-mono, ui-monospace, monospace)",
      roomFillOpacity: 0.85,
      corridorFill: "var(--map-corridor-fill, rgba(70, 85, 110, 0.28))",
    };
  }
  return {
    roomFill: "var(--surface-2)",
    roomFillActive: "var(--accent)",
    roomStroke: "var(--border)",
    roomStrokeWidth: 0.5,
    envelopeStroke: "var(--structure-stroke, var(--border))",
    envelopeStrokeWidth: 0.7,
    envelopeDasharray: undefined,
    doubleWall: false,
    showStructureFill: true,
    structureFill: activeStructure
      ? "var(--map-structure-active-fill, rgba(100, 130, 180, 0.18))"
      : "var(--map-structure-fill, rgba(120, 130, 150, 0.12))",
    structureFillActive: "var(--map-structure-active-fill, rgba(100, 130, 180, 0.18))",
    structureFillOther: "var(--map-structure-fill, rgba(120, 130, 150, 0.08))",
    labelFont: "var(--font-sans, system-ui, sans-serif)",
    roomFillOpacity: 1,
    corridorFill: "var(--map-corridor-fill, rgba(80, 90, 110, 0.15))",
  };
}

/** Outdoor/campus envelopes use dashed stroke per UI-MAP-B1. */
export function envelopeDashForKind(
  _style: ArchitectureStyle,
  kind?: string
): string | undefined {
  if (kind === "outdoor" || kind === "campus") return undefined;
  return undefined;
}
