import { useEffect, useState } from "react";
import { api, type CastCharacter } from "../api/client";
import { CharacterPossessions } from "./CharacterPossessions";
import { MemoryInspectorPanel, type MemoryInspectorSection } from "./MemoryInspectorPanel";
import { ModalShell } from "../ui/ModalShell";
import { Button } from "../ui/Button";

export type CharacterProfileRosterContext = {
  personSceneId: string | null;
  activeSceneId: string;
  locationName?: string | null;
  inventorySummary?: string;
};

export type CharacterProfileSceneOption = {
  sceneId: string;
  locationName: string;
};

type ProfileTab = "summary" | MemoryInspectorSection;

type Props = {
  worldId: string;
  characterId: string;
  displayName: string;
  rosterContext: CharacterProfileRosterContext;
  scenes: CharacterProfileSceneOption[];
  onClose: () => void;
  onGoToScene?: (sceneId: string) => void;
  onSummonHere: (characterId: string) => void | Promise<void>;
  onPlaceAt: (characterId: string, sceneId: string) => void | Promise<void>;
  onLeave: (characterId: string, sceneId: string) => void | Promise<void>;
};

function formatSceneRole(role: string): string {
  return role
    .split(/[_-]+/)
    .filter(Boolean)
    .map((word) =>
      word.length <= 3 ? word.toUpperCase() : word.charAt(0).toUpperCase() + word.slice(1)
    )
    .join(" ");
}

function presenceMeta(rosterContext: CharacterProfileRosterContext): {
  label: string;
  detail: string | null;
  variant: "here" | "away" | "unplaced";
} {
  const { personSceneId, activeSceneId, locationName } = rosterContext;
  if (!personSceneId) {
    return { label: "Unplaced", detail: null, variant: "unplaced" };
  }
  if (personSceneId === activeSceneId) {
    return {
      label: "Present here",
      detail: locationName ?? null,
      variant: "here",
    };
  }
  return {
    label: "Elsewhere",
    detail: locationName ?? null,
    variant: "away",
  };
}

const PROFILE_TABS: { id: ProfileTab; label: string }[] = [
  { id: "summary", label: "Summary" },
  { id: "memory", label: "Memory" },
  { id: "reflection", label: "Reflection" },
];

export function CharacterProfileModal({
  worldId,
  characterId,
  displayName,
  rosterContext,
  scenes,
  onClose,
  onGoToScene,
  onSummonHere,
  onPlaceAt,
  onLeave,
}: Props) {
  const [tab, setTab] = useState<ProfileTab>("summary");
  const [character, setCharacter] = useState<CastCharacter | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .listCharacters(worldId)
      .then((chars) => {
        if (cancelled) return;
        const found = chars.find((c) => c.characterId === characterId) ?? null;
        setCharacter(found);
        if (!found) setError("Character not found");
      })
      .catch(() => {
        if (!cancelled) setError("Could not load character");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [worldId, characterId]);

  const runAction = async (action: () => void | Promise<void>) => {
    setActing(true);
    try {
      await action();
      onClose();
    } finally {
      setActing(false);
    }
  };

  const initials = displayName.slice(0, 2).toUpperCase();
  const presence = presenceMeta(rosterContext);
  const persona = character?.definition?.persona?.trim();
  const instructions = character?.definition?.instructions?.trim();
  const role = character?.sceneRole?.trim();
  const { personSceneId, activeSceneId } = rosterContext;
  const isHere = personSceneId === activeSceneId;
  const isUnplaced = !personSceneId;
  const placeOptions = scenes.filter((s) => s.sceneId !== personSceneId);
  const canGoToScene =
    onGoToScene && personSceneId && personSceneId !== activeSceneId;

  const hasActions =
    canGoToScene ||
    (isHere && personSceneId) ||
    (!isHere && !isUnplaced) ||
    isUnplaced ||
    placeOptions.length > 0;

  return (
    <ModalShell
      title={displayName}
      subtitle={role ? formatSceneRole(role) : undefined}
      side="center"
      onClose={onClose}
      testId="character-profile-modal"
    >
      <div className="character-profile">
        <div className="character-profile__banner">
          <div className="character-profile__portrait" aria-hidden>
            {initials}
          </div>
          <div className="character-profile__banner-meta">
            <span
              className={`character-profile__presence character-profile__presence--${presence.variant}`}
            >
              {presence.label}
              {presence.detail ? (
                <span className="character-profile__presence-detail">{presence.detail}</span>
              ) : null}
            </span>
            {(character?.muted || character?.disabled) && (
              <div className="character-profile__flags">
                {character?.muted ? (
                  <span className="character-profile__flag">Muted</span>
                ) : null}
                {character?.disabled ? (
                  <span className="character-profile__flag">Disabled</span>
                ) : null}
              </div>
            )}
          </div>
        </div>

        <div className="ui-segmented character-profile__tabs" role="tablist" aria-label="Character views">
          {PROFILE_TABS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={tab === id}
              className={`ui-segmented__btn${tab === id ? " ui-segmented__btn--active" : ""}`}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="character-profile__content">
          {tab === "summary" ? (
            <>
              {loading && (
                <p className="character-profile__status character-profile__status--loading">
                  Loading character details…
                </p>
              )}
              {error && (
                <p className="character-profile__status character-profile__status--error">{error}</p>
              )}

              <div className="character-profile__grid">
                <section className="character-profile__card">
                  <h3 className="character-profile__card-title">Wearing &amp; holding</h3>
                  <CharacterPossessions
                    worldId={worldId}
                    characterId={characterId}
                    summaryHint={rosterContext.inventorySummary ?? character?.inventorySummary}
                  />
                </section>

                <section className="character-profile__card">
                  <h3 className="character-profile__card-title">Personality</h3>
                  {persona ? (
                    <p className="character-profile__persona">{persona}</p>
                  ) : (
                    <p className="character-profile__empty">No persona defined.</p>
                  )}
                  {instructions ? (
                    <>
                      <h3 className="character-profile__card-title character-profile__card-title--sub">
                        Instructions
                      </h3>
                      <p className="character-profile__instructions-text">{instructions}</p>
                    </>
                  ) : null}
                </section>
              </div>

              {hasActions && (
                <footer className="character-profile__footer">
                  <div className="character-profile__actions">
                    {canGoToScene && personSceneId && onGoToScene ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={acting}
                        onClick={() => runAction(() => onGoToScene(personSceneId))}
                      >
                        Go to scene
                      </Button>
                    ) : null}
                    {isHere && personSceneId ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={acting}
                        onClick={() => runAction(() => onLeave(characterId, personSceneId))}
                      >
                        Leave
                      </Button>
                    ) : null}
                    {!isHere && !isUnplaced ? (
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={acting}
                        onClick={() => runAction(() => onSummonHere(characterId))}
                      >
                        Summon here
                      </Button>
                    ) : null}
                    {isUnplaced ? (
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={acting}
                        onClick={() => runAction(() => onSummonHere(characterId))}
                      >
                        Bring here
                      </Button>
                    ) : null}
                  </div>
                  {placeOptions.length > 0 ? (
                    <label className="character-profile__place">
                      <span className="character-profile__place-label">Place at</span>
                      <select
                        className="character-profile__place-select"
                        defaultValue=""
                        disabled={acting}
                        aria-label={`Place ${displayName} at scene`}
                        onChange={(e) => {
                          const id = e.target.value;
                          if (!id) return;
                          void runAction(() => onPlaceAt(characterId, id));
                          e.target.value = "";
                        }}
                      >
                        <option value="">Choose scene…</option>
                        {placeOptions.map((s) => (
                          <option key={s.sceneId} value={s.sceneId}>
                            {s.locationName}
                            {s.sceneId === activeSceneId ? " (here)" : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                </footer>
              )}
            </>
          ) : (
            <div className="character-profile__panel">
              <MemoryInspectorPanel
                worldId={worldId}
                characterId={characterId}
                section={tab}
              />
            </div>
          )}
        </div>
      </div>
    </ModalShell>
  );
}
