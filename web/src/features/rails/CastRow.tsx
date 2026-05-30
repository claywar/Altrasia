import type { RosterPerson } from "./rosterByScene";
import type { CharacterProfileRosterContext } from "../../components/CharacterProfileModal";

type Props = {
  person: RosterPerson;
  activeSceneId: string;
  personSceneId: string | null;
  onSelectCharacter: (person: RosterPerson, context: CharacterProfileRosterContext) => void;
};

export function CastRow({ person, activeSceneId, personSceneId, onSelectCharacter }: Props) {
  const initials = person.displayName.slice(0, 2).toUpperCase();

  return (
    <li className="cast-row">
      <button
        type="button"
        className="cast-row__identity-btn"
        aria-label={`View ${person.displayName}`}
        onClick={() =>
          onSelectCharacter(person, {
            personSceneId,
            activeSceneId,
            locationName: person.locationName,
            inventorySummary: person.inventorySummary,
          })
        }
      >
        <span className="cast-row__avatar" aria-hidden>
          {initials}
        </span>
        <span className="cast-row__body">
          <span className="cast-row__name">{person.displayName}</span>
          {person.inventorySummary ? (
            <span className="cast-row__inventory" title="Worn, held, and containers">
              {person.inventorySummary}
            </span>
          ) : null}
        </span>
      </button>
    </li>
  );
}
