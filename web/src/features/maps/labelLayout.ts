import { levelsForStructure } from "./floorLevels";
import { getEnvelopePath } from "./SmoothEnvelope";
import { boxesOverlap, footprintBox } from "./layoutSpacing";
import type { MapNode, MapStructure, Point } from "./types";

export type StructureLabelPlacement = {
  structureId: string;
  x: number;
  y: number;
  text: string;
  fullName: string;
};

export type ZoneBadgePlacement = {
  structureId: string;
  x: number;
  y: number;
  text: string;
  anchor: "start" | "end";
};

function truncate(name: string, max = 18): string {
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

/** Structure title above envelope top edge, centered. */
export function structureLabels(
  structures: MapStructure[],
  nodes: MapNode[]
): StructureLabelPlacement[] {
  const labels: StructureLabelPlacement[] = [];
  const usedY: number[] = [];

  for (const st of structures) {
    const env = getEnvelopePath(st.structureId, nodes, st.boundary);
    if (!env) continue;
    let y = env.minY - 3.5;
    for (const uy of usedY) {
      if (Math.abs(uy - y) < 4) y -= 4;
    }
    usedY.push(y);
    labels.push({
      structureId: st.structureId,
      x: (env.minX + env.maxX) / 2,
      y,
      text: truncate(st.displayName.toUpperCase()),
      fullName: st.displayName,
    });
  }
  return labels;
}

/** Zone badge at upper-right inside envelope margin. */
export function zoneBadgesFromNodes(
  structures: MapStructure[],
  nodes: MapNode[]
): ZoneBadgePlacement[] {
  const byStruct = new Map<string, string>();
  for (const n of nodes) {
    if (!n.structureId || !n.mapZone) continue;
    if (!byStruct.has(n.structureId)) byStruct.set(n.structureId, n.mapZone);
  }
  const badges: ZoneBadgePlacement[] = [];
  for (const st of structures) {
    const zone = byStruct.get(st.structureId);
    if (!zone) continue;
    const env = getEnvelopePath(st.structureId, nodes, st.boundary);
    if (!env) continue;
    const structNodes = nodes.filter((n) => n.structureId === st.structureId);
    const candidates: Array<{ x: number; y: number; anchor: "start" | "end" }> = [
      { x: env.minX + 2, y: env.maxY - 1.5, anchor: "start" },
      { x: env.maxX - 2, y: env.maxY - 1.5, anchor: "end" },
      { x: env.minX + 2, y: env.minY + 2.5, anchor: "start" },
    ];
    let pick = candidates[0];
    for (const c of candidates) {
      const labelW = truncate(zone, 14).length * 1.2 + 2;
      const box =
        c.anchor === "start"
          ? { minX: c.x, maxX: c.x + labelW, minY: c.y - 2.5, maxY: c.y + 0.5 }
          : { minX: c.x - labelW, maxX: c.x, minY: c.y - 2.5, maxY: c.y + 0.5 };
      const hits = structNodes.some((n) => boxesOverlap(box, footprintBox(n), 0.5));
      if (!hits) {
        pick = c;
        break;
      }
    }
    badges.push({
      structureId: st.structureId,
      x: pick.x,
      y: pick.y,
      text: truncate(zone, 14),
      anchor: pick.anchor,
    });
  }
  return badges;
}

export function structureFloorCountLabel(
  structureId: string,
  nodes: MapNode[]
): string | null {
  const levels = levelsForStructure(nodes, structureId);
  if (levels.length <= 1) return null;
  return `${levels.length} fl`;
}

export function levelBadgeShort(mapZone?: string): string | null {
  if (!mapZone) return null;
  const m = mapZone.match(/ground|upper|basement|level|floor|ward/i);
  if (m) {
    if (/ground/i.test(mapZone)) return "Ground";
    if (/upper/i.test(mapZone)) return "Upper";
    if (/basement/i.test(mapZone)) return "B1";
  }
  return truncate(mapZone, 8);
}

export function labelsOverlap(a: Point, b: Point, minDist = 4): boolean {
  return Math.hypot(a.x - b.x, a.y - b.y) < minDist;
}
