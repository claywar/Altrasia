export type RosterPerson = {
  characterId: string;
  displayName: string;
  sceneId?: string | null;
  locationName?: string | null;
  presentSceneId?: string | null;
  inventorySummary?: string;
};

export type Roster = {
  atLocation: RosterPerson[];
  elsewhere: RosterPerson[];
  unplaced?: RosterPerson[];
};

export type PlaceRow = {
  scene: { sceneId: string; locationName: string; presentJson?: string };
  actionLabel: string | null;
};

export type PlaceGroup = {
  key: string;
  title: string;
  levels: { key: string; title: string; rows: PlaceRow[] }[];
};

function sceneIdFor(person: RosterPerson): string | null {
  return person.sceneId ?? person.presentSceneId ?? null;
}

function sortPeople(people: RosterPerson[]): RosterPerson[] {
  return [...people].sort((a, b) => a.displayName.localeCompare(b.displayName));
}

/** Merge atLocation + elsewhere into a map keyed by sceneId. */
export function rosterByScene(roster: Roster): {
  byScene: Map<string, RosterPerson[]>;
  unplaced: RosterPerson[];
} {
  const byScene = new Map<string, RosterPerson[]>();
  for (const person of [...roster.atLocation, ...roster.elsewhere]) {
    const sid = sceneIdFor(person);
    if (!sid) continue;
    const list = byScene.get(sid) ?? [];
    list.push(person);
    byScene.set(sid, list);
  }
  for (const [sid, list] of byScene) {
    byScene.set(sid, sortPeople(list));
  }
  return {
    byScene,
    unplaced: sortPeople(roster.unplaced ?? []),
  };
}

function findRowInGroups(
  groups: PlaceGroup[],
  activeSceneId: string
): { row: PlaceRow; groupKey: string; levelKey: string } | null {
  for (const group of groups) {
    for (const level of group.levels) {
      const row = level.rows.find((r) => r.scene.sceneId === activeSceneId);
      if (row) return { row, groupKey: group.key, levelKey: level.key };
    }
  }
  return null;
}

function removeRowFromGroups(groups: PlaceGroup[], activeSceneId: string): PlaceGroup[] {
  return groups
    .map((group) => ({
      ...group,
      levels: group.levels
        .map((level) => ({
          ...level,
          rows: level.rows.filter((r) => r.scene.sceneId !== activeSceneId),
        }))
        .filter((level) => level.rows.length > 0),
    }))
    .filter((group) => group.levels.length > 0);
}

/** Hoist active scene to top; remove duplicate from structure tree. */
export function sortWorldRailGroups(
  groups: PlaceGroup[],
  activeSceneId: string,
  isFlat = false
): {
  activeRow: PlaceRow | null;
  groupsWithoutActive: PlaceGroup[];
  flatRest: PlaceRow[];
} {
  const found = findRowInGroups(groups, activeSceneId);
  const groupsWithoutActive = removeRowFromGroups(groups, activeSceneId);

  if (isFlat && groups.length >= 1 && groups[0]?.levels.length === 1) {
    const all = groups[0].levels[0]?.rows ?? [];
    const activeRow = all.find((r) => r.scene.sceneId === activeSceneId) ?? null;
    const flatRest = all
      .filter((r) => r.scene.sceneId !== activeSceneId)
      .sort((a, b) => a.scene.locationName.localeCompare(b.scene.locationName));
    return { activeRow, groupsWithoutActive: [], flatRest };
  }

  return {
    activeRow: found?.row ?? null,
    groupsWithoutActive,
    flatRest: [],
  };
}
