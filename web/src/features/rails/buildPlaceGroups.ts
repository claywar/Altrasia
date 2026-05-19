import type { Scene, SpatialGraph } from "../../api/client";
import { levelLabelFor, nodeLevelIndex } from "../maps/floorLevels";
import type { MapGraph, MapNode } from "../maps/types";
import type { PlaceGroup, PlaceRow } from "./rosterByScene";

export function placeActionLabel(
  sceneId: string,
  activeSceneId: string,
  adjacent: boolean,
  reachable?: Set<string>
): string | null {
  if (sceneId === activeSceneId) return null;
  if (adjacent) return "Go";
  if (reachable?.has(sceneId)) return "Jump";
  return null;
}

export function buildPlaceGroups(
  scenes: Scene[],
  graph: SpatialGraph | null | undefined,
  activeSceneId: string,
  adjacentIds: Set<string>,
  reachableSceneIds?: Set<string>
): PlaceGroup[] {
  const nodeByScene = new Map(
    (graph?.nodes ?? []).map((n) => [n.sceneId, n as MapNode])
  );
  const structNames = new Map(
    (graph?.structures ?? []).map((s) => [s.structureId, s.displayName])
  );

  const byStruct = new Map<string, Map<number, PlaceRow[]>>();

  for (const scene of scenes) {
    const node = nodeByScene.get(scene.sceneId);
    const structId = node?.structureId ?? "__outdoors__";
    const level = node ? nodeLevelIndex(node) : 0;
    const row: PlaceRow = {
      scene,
      actionLabel: placeActionLabel(
        scene.sceneId,
        activeSceneId,
        adjacentIds.has(scene.sceneId),
        reachableSceneIds
      ),
    };
    if (!byStruct.has(structId)) byStruct.set(structId, new Map());
    const levels = byStruct.get(structId)!;
    if (!levels.has(level)) levels.set(level, []);
    levels.get(level)!.push(row);
  }

  const result: PlaceGroup[] = [];
  const structIds = [...byStruct.keys()].sort((a, b) => {
    if (a === "__outdoors__") return 1;
    if (b === "__outdoors__") return -1;
    return (structNames.get(a) ?? a).localeCompare(structNames.get(b) ?? "");
  });

  const mg = graph as MapGraph | undefined;

  for (const structId of structIds) {
    const levels = byStruct.get(structId)!;
    const levelKeys = [...levels.keys()].sort((a, b) => a - b);
    const title =
      structId === "__outdoors__"
        ? "Outdoors"
        : (structNames.get(structId) ?? structId);
    result.push({
      key: structId,
      title,
      levels: levelKeys.map((lvl) => ({
        key: `${structId}-${lvl}`,
        title:
          structId === "__outdoors__"
            ? "Sites"
            : mg
              ? levelLabelFor(mg.nodes, structId, lvl)
              : lvl === 0
                ? "Ground floor"
                : `Level ${lvl}`,
        rows: levels.get(lvl)!.sort((a, b) =>
          a.scene.locationName.localeCompare(b.scene.locationName)
        ),
      })),
    });
  }
  return result;
}

export function adjacentSceneIds(
  graph: SpatialGraph | null | undefined,
  activeSceneId: string
): Set<string> {
  if (!graph) return new Set<string>();
  const out = new Set<string>();
  for (const e of graph.edges) {
    if (e.sourceSceneId === activeSceneId) out.add(e.targetSceneId);
    if (e.targetSceneId === activeSceneId) out.add(e.sourceSceneId);
  }
  return out;
}
