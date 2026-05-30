import { useMemo, useState } from "react";
import { type Scene, type SpatialGraph } from "../../api/client";
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
import type { CharacterProfileRosterContext } from "../../components/CharacterProfileModal";

type Props = {
  scenes: Scene[];
  activeSceneId: string;
  graph?: SpatialGraph | null;
  reachableSceneIds?: Set<string>;
  roster: Roster;
  onSelect: (sceneId: string) => void;
  onSelectCharacter: (person: RosterPerson, context: CharacterProfileRosterContext) => void;
};

function personSceneId(person: RosterPerson): string | null {
  return person.sceneId ?? person.presentSceneId ?? null;
}

function PlaceSceneBlock({
  row,
  active,
  cast,
  activeSceneId,
  forceExpanded,
  onSelect,
  onSelectCharacter,
}: {
  row: PlaceRow;
  active: boolean;
  cast: RosterPerson[];
  activeSceneId: string;
  forceExpanded?: boolean;
  onSelect: (sceneId: string) => void;
  onSelectCharacter: (person: RosterPerson, context: CharacterProfileRosterContext) => void;
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
          <span className="place-card__label">
            <span className="place-card__name">{row.scene.locationName}</span>
            {cast.length > 0 && (
              <span
                className="place-card__badge"
                aria-label={`${cast.length} present`}
              >
                {cast.length}
              </span>
            )}
          </span>
          <span className="place-card__action" aria-hidden={!row.actionLabel}>
            {row.actionLabel ?? ""}
          </span>
        </button>
        {forceExpanded ? (
          <span className="place-scene__toggle-spacer" aria-hidden />
        ) : (
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
                onSelectCharacter={onSelectCharacter}
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
  activeSceneId,
  onSelectCharacter,
}: {
  unplaced: RosterPerson[];
  activeSceneId: string;
  onSelectCharacter: (person: RosterPerson, context: CharacterProfileRosterContext) => void;
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
              onSelectCharacter={onSelectCharacter}
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
  forceExpanded: boolean,
  handlers: {
    onSelect: (sceneId: string) => void;
    onSelectCharacter: (person: RosterPerson, context: CharacterProfileRosterContext) => void;
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
      activeSceneId={activeSceneId}
      forceExpanded={forceExpanded}
      {...handlers}
    />
  );
}

export function WorldRail({
  scenes,
  activeSceneId,
  graph,
  reachableSceneIds,
  roster,
  onSelect,
  onSelectCharacter,
}: Props) {
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

  const handlers = { onSelect, onSelectCharacter };

  return (
    <RailSection title="World" testId="world-rail" className="world-rail">
      <ul className="places-list world-rail__scenes">
        {activeRow &&
          renderSceneBlock(activeRow, activeSceneId, byScene, true, handlers)}
      </ul>

      {(groupsWithoutActive.length > 0 || flatRest.length > 0) && activeRow && (
        <hr className="world-rail__divider" aria-hidden />
      )}

      {flat ? (
        <ul className="places-list world-rail__scenes">
          {flatRest.map((row) =>
            renderSceneBlock(row, activeSceneId, byScene, false, handlers)
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
                      renderSceneBlock(row, activeSceneId, byScene, false, handlers)
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
        activeSceneId={activeSceneId}
        onSelectCharacter={onSelectCharacter}
      />
    </RailSection>
  );
}
