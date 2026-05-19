import { useMemo, useState } from "react";
import { api, type Scene, type SpatialGraph } from "../../api/client";
import { RailSection } from "../../ui/RailSection";
import { adjacentSceneIds, buildPlaceGroups, placeActionLabel } from "./buildPlaceGroups";
import { CastRow } from "./CastRow";
import {
  rosterByScene,
  sortWorldRailGroups,
  type PlaceRow,
  type Roster,
  type RosterPerson,
} from "./rosterByScene";

type SceneOption = { sceneId: string; locationName: string };

type Props = {
  worldId: string;
  scenes: Scene[];
  activeSceneId: string;
  graph?: SpatialGraph | null;
  reachableSceneIds?: Set<string>;
  roster: Roster;
  onSelect: (sceneId: string) => void;
  onMemory: (characterId: string, displayName: string) => void;
  onPresenceChanged: () => void;
};

function personSceneId(person: RosterPerson): string | null {
  return person.sceneId ?? person.presentSceneId ?? null;
}

function PlaceSceneBlock({
  row,
  active,
  cast,
  sceneOptions,
  activeSceneId,
  forceExpanded,
  onSelect,
  onMemory,
  onSummonHere,
  onPlaceAt,
  onLeave,
}: {
  row: PlaceRow;
  active: boolean;
  cast: RosterPerson[];
  sceneOptions: SceneOption[];
  activeSceneId: string;
  forceExpanded?: boolean;
  onSelect: (sceneId: string) => void;
  onMemory: (characterId: string, displayName: string) => void;
  onSummonHere: (characterId: string) => void;
  onPlaceAt: (characterId: string, sceneId: string) => void;
  onLeave: (characterId: string, sceneId: string) => void;
}) {
  const occupied = cast.length > 0;
  const [expanded, setExpanded] = useState(occupied || active);
  const isExpanded = forceExpanded || expanded;
  const sceneId = row.scene.sceneId;

  const toggleCast = () => {
    if (!forceExpanded) setExpanded((v) => !v);
  };

  return (
    <li className={`place-scene${active ? " place-scene--active" : ""}`}>
      <div className="place-scene__header">
        <button
          type="button"
          className={`place-card${active ? " place-card--active" : ""}`}
          onClick={() => onSelect(sceneId)}
        >
          <span className="place-card__name">{row.scene.locationName}</span>
          {row.actionLabel && (
            <span className="place-card__action" aria-hidden>
              {row.actionLabel}
            </span>
          )}
          {cast.length > 0 && (
            <span className="place-card__badge" aria-label={`${cast.length} present`}>
              {cast.length}
            </span>
          )}
        </button>
        {!forceExpanded && (
          <button
            type="button"
            className="place-scene__toggle"
            aria-expanded={isExpanded}
            aria-label={`${isExpanded ? "Collapse" : "Expand"} cast at ${row.scene.locationName}`}
            onClick={toggleCast}
          >
            {isExpanded ? "−" : "+"}
          </button>
        )}
      </div>
      {isExpanded && (
        <ul className="place-scene__cast">
          {cast.length === 0 ? (
            <li className="place-scene__empty">Empty</li>
          ) : (
            cast.map((person) => (
              <CastRow
                key={person.characterId}
                person={person}
                activeSceneId={activeSceneId}
                personSceneId={personSceneId(person) ?? sceneId}
                scenes={sceneOptions}
                onMemory={onMemory}
                onSummonHere={onSummonHere}
                onPlaceAt={onPlaceAt}
                onLeave={onLeave}
                onGoToScene={onSelect}
              />
            ))
          )}
        </ul>
      )}
    </li>
  );
}

function OffStageBlock({
  unplaced,
  sceneOptions,
  activeSceneId,
  onMemory,
  onSummonHere,
  onPlaceAt,
  onLeave,
}: {
  unplaced: RosterPerson[];
  sceneOptions: SceneOption[];
  activeSceneId: string;
  onMemory: (characterId: string, displayName: string) => void;
  onSummonHere: (characterId: string) => void;
  onPlaceAt: (characterId: string, sceneId: string) => void;
  onLeave: (characterId: string, sceneId: string) => void;
}) {
  const [open, setOpen] = useState(unplaced.length > 0);
  if (unplaced.length === 0) return null;

  return (
    <section className="world-rail__offstage">
      <button
        type="button"
        className="world-rail__offstage-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        Off-stage ({unplaced.length})
      </button>
      {open && (
        <ul className="place-scene__cast">
          {unplaced.map((person) => (
            <CastRow
              key={person.characterId}
              person={person}
              activeSceneId={activeSceneId}
              personSceneId={null}
              scenes={sceneOptions}
              onMemory={onMemory}
              onSummonHere={onSummonHere}
              onPlaceAt={onPlaceAt}
              onLeave={onLeave}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function renderSceneBlock(
  row: PlaceRow,
  activeSceneId: string,
  byScene: Map<string, RosterPerson[]>,
  sceneOptions: SceneOption[],
  forceExpanded: boolean,
  handlers: {
    onSelect: (sceneId: string) => void;
    onMemory: (characterId: string, displayName: string) => void;
    onSummonHere: (characterId: string) => void;
    onPlaceAt: (characterId: string, sceneId: string) => void;
    onLeave: (characterId: string, sceneId: string) => void;
  }
) {
  const sceneId = row.scene.sceneId;
  const cast = byScene.get(sceneId) ?? [];
  return (
    <PlaceSceneBlock
      key={sceneId}
      row={row}
      active={sceneId === activeSceneId}
      cast={cast}
      sceneOptions={sceneOptions}
      activeSceneId={activeSceneId}
      forceExpanded={forceExpanded}
      {...handlers}
    />
  );
}

export function WorldRail({
  worldId,
  scenes,
  activeSceneId,
  graph,
  reachableSceneIds,
  roster,
  onSelect,
  onMemory,
  onPresenceChanged,
}: Props) {
  const sceneOptions = useMemo(
    () => scenes.map((s) => ({ sceneId: s.sceneId, locationName: s.locationName })),
    [scenes]
  );

  const { byScene, unplaced } = useMemo(() => rosterByScene(roster), [roster]);

  const adjacentIds = useMemo(
    () => adjacentSceneIds(graph, activeSceneId),
    [graph, activeSceneId]
  );

  const groups = useMemo(
    () => buildPlaceGroups(scenes, graph, activeSceneId, adjacentIds, reachableSceneIds),
    [scenes, graph, activeSceneId, adjacentIds, reachableSceneIds]
  );

  const flat = !graph?.structures?.length && groups.length <= 1;

  const sorted = useMemo(
    () => sortWorldRailGroups(groups, activeSceneId, flat),
    [groups, activeSceneId, flat]
  );

  const activeRow = useMemo(() => {
    if (sorted.activeRow) return sorted.activeRow;
    const scene = scenes.find((s) => s.sceneId === activeSceneId);
    if (!scene) return null;
    return {
      scene,
      actionLabel: placeActionLabel(
        scene.sceneId,
        activeSceneId,
        adjacentIds.has(scene.sceneId),
        reachableSceneIds
      ),
    };
  }, [sorted.activeRow, scenes, activeSceneId, adjacentIds, reachableSceneIds]);

  const { groupsWithoutActive, flatRest } = sorted;

  const summonHere = async (characterId: string) => {
    await api.summonPresence(worldId, {
      characterIds: [characterId],
      targetSceneId: activeSceneId,
    });
    onPresenceChanged();
  };

  const placeAt = async (characterId: string, sceneId: string) => {
    await api.joinPresence(worldId, sceneId, characterId);
    onPresenceChanged();
  };

  const leaveScene = async (characterId: string, sceneId: string) => {
    await api.leavePresence(worldId, sceneId, characterId);
    onPresenceChanged();
  };

  const handlers = {
    onSelect,
    onMemory,
    onSummonHere: summonHere,
    onPlaceAt: placeAt,
    onLeave: leaveScene,
  };

  return (
    <RailSection title="World" testId="world-rail" className="world-rail">
      <ul className="places-list world-rail__scenes">
        {activeRow &&
          renderSceneBlock(activeRow, activeSceneId, byScene, sceneOptions, true, handlers)}
      </ul>

      {(groupsWithoutActive.length > 0 || flatRest.length > 0) && activeRow && (
        <hr className="world-rail__divider" aria-hidden />
      )}

      {flat ? (
        <ul className="places-list world-rail__scenes">
          {flatRest.map((row) =>
            renderSceneBlock(row, activeSceneId, byScene, sceneOptions, false, handlers)
          )}
        </ul>
      ) : (
        <div className="places-groups">
          {groupsWithoutActive.map((group) => (
            <section key={group.key} className="places-group">
              <h3 className="places-group__title">{group.title}</h3>
              {group.levels.map((level) => (
                <div key={level.key} className="places-level">
                  {group.levels.length > 1 && (
                    <h4 className="places-level__title">{level.title}</h4>
                  )}
                  <ul className="places-list world-rail__scenes">
                    {level.rows.map((row) =>
                      renderSceneBlock(
                        row,
                        activeSceneId,
                        byScene,
                        sceneOptions,
                        false,
                        handlers
                      )
                    )}
                  </ul>
                </div>
              ))}
            </section>
          ))}
        </div>
      )}

      <OffStageBlock
        unplaced={unplaced}
        sceneOptions={sceneOptions}
        activeSceneId={activeSceneId}
        onMemory={onMemory}
        onSummonHere={summonHere}
        onPlaceAt={placeAt}
        onLeave={leaveScene}
      />
    </RailSection>
  );
}
