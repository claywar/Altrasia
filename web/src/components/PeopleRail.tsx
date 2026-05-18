import { api } from "../api/client";
import { RailSection } from "../ui/RailSection";

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

type SceneOption = {
  sceneId: string;
  locationName: string;
};

type Props = {
  worldId: string;
  activeSceneId: string;
  scenes: SceneOption[];
  roster: Roster;
  onMemory: (characterId: string, displayName: string) => void;
  onPresenceChanged: () => void;
};

function PlaceAtSelect({
  scenes,
  currentSceneId,
  activeSceneId,
  onSelect,
}: {
  scenes: SceneOption[];
  currentSceneId: string | null | undefined;
  activeSceneId: string;
  onSelect: (sceneId: string) => void;
}) {
  const options = scenes.filter((s) => s.sceneId !== currentSceneId);
  if (options.length === 0) return null;
  return (
    <select
      className="people-place-select"
      defaultValue=""
      aria-label="Place at scene"
      onChange={(e) => {
        const id = e.target.value;
        if (id) onSelect(id);
        e.target.value = "";
      }}
    >
      <option value="">Place at…</option>
      {options.map((s) => (
        <option key={s.sceneId} value={s.sceneId}>
          {s.locationName}
          {s.sceneId === activeSceneId ? " (here)" : ""}
        </option>
      ))}
    </select>
  );
}

export function PeopleRail({
  worldId,
  activeSceneId,
  scenes,
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

  const placeAt = async (characterId: string, sceneId: string) => {
    await api.joinPresence(worldId, sceneId, characterId);
    onPresenceChanged();
  };

  const leaveScene = async (characterId: string, sceneId: string) => {
    await api.leavePresence(worldId, sceneId, characterId);
    onPresenceChanged();
  };

  return (
    <RailSection title="People" testId="people-rail">
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
              <PlaceAtSelect
                scenes={scenes}
                currentSceneId={p.sceneId ?? activeSceneId}
                activeSceneId={activeSceneId}
                onSelect={(sid) => placeAt(p.characterId, sid)}
              />
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
              <PlaceAtSelect
                scenes={scenes}
                currentSceneId={p.sceneId ?? p.presentSceneId}
                activeSceneId={activeSceneId}
                onSelect={(sid) => placeAt(p.characterId, sid)}
              />
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
              <PlaceAtSelect
                scenes={scenes}
                currentSceneId={null}
                activeSceneId={activeSceneId}
                onSelect={(sid) => placeAt(p.characterId, sid)}
              />
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
    </RailSection>
  );
}
