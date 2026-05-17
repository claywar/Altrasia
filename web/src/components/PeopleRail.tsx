import { api } from "../api/client";

export type RosterPerson = {
  characterId: string;
  displayName: string;
  sceneId?: string | null;
  locationName?: string | null;
  presentSceneId?: string | null;
};

type Roster = {
  atLocation: RosterPerson[];
  elsewhere: RosterPerson[];
  unplaced?: RosterPerson[];
};

type Props = {
  worldId: string;
  activeSceneId: string;
  roster: Roster;
  onMemory: (characterId: string, displayName: string) => void;
  onPresenceChanged: () => void;
};

export function PeopleRail({
  worldId,
  activeSceneId,
  roster,
  onMemory,
  onPresenceChanged,
}: Props) {
  const summonHere = async (characterId: string) => {
    await api.summonPresence(worldId, {
      characterIds: [characterId],
      targetSceneId: activeSceneId,
    });
    onPresenceChanged();
  };

  const leaveScene = async (characterId: string, sceneId: string) => {
    await api.leavePresence(worldId, sceneId, characterId);
    onPresenceChanged();
  };

  return (
    <div className="rail-section">
      <h3>People</h3>
      <ul className="rail-list">
        {roster.atLocation.map((p) => (
          <li key={p.characterId} className="people-row">
            <span>{p.displayName} (here)</span>
            <div className="people-actions">
              <button
                type="button"
                className="people-memory"
                onClick={() => onMemory(p.characterId, p.displayName)}
              >
                Memory
              </button>
              {p.sceneId && (
                <button
                  type="button"
                  className="people-secondary"
                  onClick={() => leaveScene(p.characterId, p.sceneId!)}
                >
                  Leave
                </button>
              )}
            </div>
          </li>
        ))}
        {roster.elsewhere.map((p) => (
          <li key={p.characterId} className="people-row">
            <span>
              {p.displayName} — {p.locationName ?? "another scene"}
            </span>
            <div className="people-actions">
              <button
                type="button"
                className="people-secondary"
                onClick={() => summonHere(p.characterId)}
              >
                Summon here
              </button>
              <button
                type="button"
                className="people-memory"
                onClick={() => onMemory(p.characterId, p.displayName)}
              >
                Memory
              </button>
            </div>
          </li>
        ))}
        {(roster.unplaced ?? []).map((p) => (
          <li key={p.characterId} className="people-row unplaced">
            <span>{p.displayName} (unplaced)</span>
            <div className="people-actions">
              <button
                type="button"
                className="people-secondary"
                onClick={() => summonHere(p.characterId)}
              >
                Bring here
              </button>
              <button
                type="button"
                className="people-memory"
                onClick={() => onMemory(p.characterId, p.displayName)}
              >
                Memory
              </button>
            </div>
          </li>
        ))}
        {roster.atLocation.length === 0 &&
          roster.elsewhere.length === 0 &&
          (roster.unplaced?.length ?? 0) === 0 && (
            <li style={{ color: "var(--muted)" }}>No cast</li>
          )}
      </ul>
    </div>
  );
}
