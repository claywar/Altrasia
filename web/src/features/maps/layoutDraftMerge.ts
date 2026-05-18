import type { LayoutDraft, SpatialGraph } from "../../api/client";
import { readPlanPosition } from "./diagramModel";
import type { MapStructure } from "./types";

type DraftSceneItem = {
  sceneId: string;
  mapPosition?: { x: number; y: number };
  planPosition?: { x: number; y: number };
  levelIndex?: number;
  mapLevel?: number;
  structureId?: string;
};

type DraftStructureItem = {
  structureId: string;
  displayName?: string;
  boundary?: MapStructure["boundary"];
  kind?: string;
};

function draftSceneItems(proposed: LayoutDraft["proposed"]): DraftSceneItem[] {
  const raw = proposed?.nodes ?? proposed?.scenes ?? [];
  return raw.map((item) => ({
    sceneId: String(item.sceneId),
    mapPosition: item.mapPosition as DraftSceneItem["mapPosition"],
    planPosition: (item as DraftSceneItem).planPosition,
    levelIndex: (item as DraftSceneItem).levelIndex,
    mapLevel: (item as DraftSceneItem).mapLevel,
    structureId: (item as DraftSceneItem).structureId,
  }));
}

function draftStructures(
  proposed: LayoutDraft["proposed"]
): DraftStructureItem[] | undefined {
  if (!proposed?.structures?.length) return undefined;
  return proposed.structures.map((st) => ({
    structureId: String(st.structureId),
    displayName: st.displayName as string | undefined,
    boundary: st.boundary as DraftStructureItem["boundary"],
    kind: st.kind as string | undefined,
  }));
}

export function mergeDraftToGraph(
  proposed: LayoutDraft["proposed"],
  base: SpatialGraph | null | undefined
): SpatialGraph | null {
  if (!proposed && !base) return null;
  const sceneItems = draftSceneItems(proposed);
  if (!sceneItems.length && base) {
    const structs = draftStructures(proposed);
    if (!proposed?.worldMap && !structs?.length) return base;
    return {
      ...base,
      structures: structs ? mergeStructures(structs, base.structures) : base.structures,
      worldMap: proposed?.worldMap ?? base.worldMap,
    };
  }

  const nodeById = new Map((base?.nodes ?? []).map((n) => [n.sceneId, n]));

  const nodes: SpatialGraph["nodes"] = sceneItems.map((item) => {
    const existing = nodeById.get(item.sceneId);
    const pos = item.mapPosition ?? existing?.layout ?? { x: 50, y: 50 };
    const plan = item.planPosition ?? pos;
    return {
      sceneId: item.sceneId,
      locationName: existing?.locationName ?? item.sceneId,
      isActive: existing?.isActive ?? false,
      layout: pos,
      planPosition: plan,
      presentCount: existing?.presentCount ?? 0,
      structureId: item.structureId ?? existing?.structureId,
      mapZone: existing?.mapZone,
      mapShape: existing?.mapShape,
      mapSize: existing?.mapSize,
      levelIndex: item.levelIndex ?? existing?.levelIndex,
      mapLevel: item.mapLevel ?? existing?.mapLevel,
      levelLabel: existing?.levelLabel,
      locationDescription: existing?.locationDescription,
    };
  });

  const mergedIds = new Set(nodes.map((n) => n.sceneId));
  for (const n of base?.nodes ?? []) {
    if (!mergedIds.has(n.sceneId)) nodes.push(n);
  }

  return {
    activeSceneId: base?.activeSceneId ?? "",
    nodes,
    edges: base?.edges ?? [],
    structures: draftStructures(proposed)
      ? mergeStructures(draftStructures(proposed)!, base?.structures)
      : base?.structures,
    worldMap: proposed?.worldMap ?? base?.worldMap,
    layout: base?.layout,
    verticalEdges: base?.verticalEdges,
  };
}

function mergeStructures(
  proposed: DraftStructureItem[],
  base: SpatialGraph["structures"]
): SpatialGraph["structures"] {
  if (!proposed.length) return base;
  const byId = new Map((base ?? []).map((s) => [s.structureId, s]));
  for (const st of proposed) {
    if (!st.structureId) continue;
    byId.set(st.structureId, {
      ...(byId.get(st.structureId) ?? {
        structureId: st.structureId,
        displayName: st.structureId,
      }),
      ...st,
      displayName: st.displayName ?? byId.get(st.structureId)?.displayName ?? st.structureId,
    });
  }
  return [...byId.values()];
}

/** Normalize merged nodes for stack preview alignment. */
export function ensurePlanPositions(graph: SpatialGraph): SpatialGraph {
  return {
    ...graph,
    nodes: graph.nodes.map((n) => {
      const p = readPlanPosition(n);
      return { ...n, layout: p, planPosition: p };
    }),
  };
}
