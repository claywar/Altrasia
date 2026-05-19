import { useMemo } from "react";
import type { Scene, SpatialGraph } from "../../api/client";
import { levelLabelFor, nodeLevelIndex } from "../maps/floorLevels";
import type { MapGraph, MapNode } from "../maps/types";
import { RailSection } from "../../ui/RailSection";

type Props = {
  scenes: Scene[];
  activeSceneId: string;
  graph?: SpatialGraph | null;
  reachableSceneIds?: Set<string>;
  onSelect: (sceneId: string) => void;
};

type PlaceRow = {
  scene: Scene;
  node?: MapNode;
  actionLabel: string | null;
};

type PlaceGroup = {
  key: string;
  title: string;
  levels: { key: string; title: string; rows: PlaceRow[] }[];
};

function actionLabel(
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

function presentCount(scene: Scene): number {
  try {
    return JSON.parse(scene.presentJson || "[]").length;
  } catch {
    return 0;
  }
}

function PlaceCard({
  row,
  active,
  onSelect,
}: {
  row: PlaceRow;
  active: boolean;
  onSelect: (sceneId: string) => void;
}) {
  const count = presentCount(row.scene);
  return (
    <li>
      <button
        type="button"
        className={`place-card${active ? " place-card--active" : ""}`}
        onClick={() => onSelect(row.scene.sceneId)}
      >
        <span className="place-card__name">{row.scene.locationName}</span>
        {row.actionLabel && (
          <span className="place-card__action" aria-hidden>
            {row.actionLabel}
          </span>
        )}
        {count > 0 && (
          <span className="place-card__badge" aria-label={`${count} present`}>
            {count}
          </span>
        )}
      </button>
    </li>
  );
}

export function PlacesRail({
  scenes,
  activeSceneId,
  graph,
  reachableSceneIds,
  onSelect,
}: Props) {
  const adjacentIds = useMemo(() => {
    if (!graph) return new Set<string>();
    const out = new Set<string>();
    for (const e of graph.edges) {
      if (e.sourceSceneId === activeSceneId) out.add(e.targetSceneId);
      if (e.targetSceneId === activeSceneId) out.add(e.sourceSceneId);
    }
    return out;
  }, [graph, activeSceneId]);

  const groups = useMemo((): PlaceGroup[] => {
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
        node,
        actionLabel: actionLabel(
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

    for (const structId of structIds) {
      const levels = byStruct.get(structId)!;
      const levelKeys = [...levels.keys()].sort((a, b) => a - b);
      const mg = graph as MapGraph | undefined;
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
  }, [scenes, graph, activeSceneId, adjacentIds, reachableSceneIds]);

  const flat = !graph?.structures?.length && groups.length <= 1;

  if (flat) {
    const rows = groups[0]?.levels[0]?.rows ?? scenes.map((scene) => ({
      scene,
      actionLabel: actionLabel(
        scene.sceneId,
        activeSceneId,
        adjacentIds.has(scene.sceneId),
        reachableSceneIds
      ),
    }));
    return (
      <RailSection title="Places" testId="places-rail">
        <ul className="places-list">
          {rows.map((row) => (
            <PlaceCard
              key={row.scene.sceneId}
              row={row}
              active={row.scene.sceneId === activeSceneId}
              onSelect={onSelect}
            />
          ))}
        </ul>
      </RailSection>
    );
  }

  return (
    <RailSection title="Places" testId="places-rail">
      <div className="places-groups">
        {groups.map((group) => (
          <section key={group.key} className="places-group">
            <h3 className="places-group__title">{group.title}</h3>
            {group.levels.map((level) => (
              <div key={level.key} className="places-level">
                {group.levels.length > 1 && (
                  <h4 className="places-level__title">{level.title}</h4>
                )}
                <ul className="places-list">
                  {level.rows.map((row) => (
                    <PlaceCard
                      key={row.scene.sceneId}
                      row={row}
                      active={row.scene.sceneId === activeSceneId}
                      onSelect={onSelect}
                    />
                  ))}
                </ul>
              </div>
            ))}
          </section>
        ))}
      </div>
    </RailSection>
  );
}
