import { useRef, useEffect, useState, type ReactNode } from "react";
import type { RosterPerson } from "./rosterByScene";

type SceneOption = { sceneId: string; locationName: string };

type Props = {
  person: RosterPerson;
  activeSceneId: string;
  personSceneId: string | null;
  scenes: SceneOption[];
  onMemory: (characterId: string, displayName: string) => void;
  onSummonHere: (characterId: string) => void;
  onPlaceAt: (characterId: string, sceneId: string) => void;
  onLeave: (characterId: string, sceneId: string) => void;
  onGoToScene?: (sceneId: string) => void;
};

function CastMenu({
  personName,
  open,
  onClose,
  onToggle,
  children,
}: {
  personName: string;
  open: boolean;
  onClose: () => void;
  onToggle: () => void;
  children: ReactNode;
}) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open, onClose]);

  return (
    <div ref={menuRef} className="cast-row__menu">
      <button
        type="button"
        className="cast-row__menu-btn"
        aria-label={`Actions for ${personName}`}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={onToggle}
      >
        ⋯
      </button>
      {open && (
        <div className="cast-row__menu-panel" role="menu">
          {children}
        </div>
      )}
    </div>
  );
}

export function CastRow({
  person,
  activeSceneId,
  personSceneId,
  scenes,
  onMemory,
  onSummonHere,
  onPlaceAt,
  onLeave,
  onGoToScene,
}: Props) {
  const [open, setOpen] = useState(false);
  const initials = person.displayName.slice(0, 2).toUpperCase();
  const isHere = personSceneId === activeSceneId;
  const isUnplaced = !personSceneId;
  const placeOptions = scenes.filter((s) => s.sceneId !== personSceneId);

  const close = () => setOpen(false);

  return (
    <li className="cast-row">
      <span className="cast-row__avatar" aria-hidden>
        {initials}
      </span>
      <span className="cast-row__name">{person.displayName}</span>
      <CastMenu
        personName={person.displayName}
        open={open}
        onClose={close}
        onToggle={() => setOpen((v) => !v)}
      >
        <button
          type="button"
          className="cast-row__menu-item"
          role="menuitem"
          onClick={() => {
            onMemory(person.characterId, person.displayName);
            close();
          }}
        >
          Memory
        </button>
        {isHere && personSceneId && (
          <button
            type="button"
            className="cast-row__menu-item"
            role="menuitem"
            onClick={() => {
              onLeave(person.characterId, personSceneId);
              close();
            }}
          >
            Leave
          </button>
        )}
        {!isHere && !isUnplaced && (
          <>
            {onGoToScene && personSceneId && (
              <button
                type="button"
                className="cast-row__menu-item"
                role="menuitem"
                onClick={() => {
                  onGoToScene(personSceneId);
                  close();
                }}
              >
                Go to scene
              </button>
            )}
            <button
              type="button"
              className="cast-row__menu-item"
              role="menuitem"
              onClick={() => {
                onSummonHere(person.characterId);
                close();
              }}
            >
              Summon here
            </button>
          </>
        )}
        {isUnplaced && (
          <button
            type="button"
            className="cast-row__menu-item"
            role="menuitem"
            onClick={() => {
              onSummonHere(person.characterId);
              close();
            }}
          >
            Bring here
          </button>
        )}
        {placeOptions.length > 0 && (
          <label className="cast-row__menu-place">
            <span className="cast-row__menu-place-label">Place at…</span>
            <select
              className="people-place-select"
              defaultValue=""
              aria-label={`Place ${person.displayName} at scene`}
              onChange={(e) => {
                const id = e.target.value;
                if (id) onPlaceAt(person.characterId, id);
                e.target.value = "";
                close();
              }}
            >
              <option value="">Choose…</option>
              {placeOptions.map((s) => (
                <option key={s.sceneId} value={s.sceneId}>
                  {s.locationName}
                  {s.sceneId === activeSceneId ? " (here)" : ""}
                </option>
              ))}
            </select>
          </label>
        )}
      </CastMenu>
    </li>
  );
}
