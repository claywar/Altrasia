import type { Scene } from "../../api/client";
import { RailSection } from "../../ui/RailSection";

type Props = {
  scenes: Scene[];
  activeSceneId: string;
  onSelect: (sceneId: string) => void;
};

export function PlacesRail({ scenes, activeSceneId, onSelect }: Props) {
  return (
    <RailSection title="Places" testId="places-rail">
      <ul className="places-list">
        {scenes.map((s) => {
          const active = s.sceneId === activeSceneId;
          let presentCount = 0;
          try {
            presentCount = JSON.parse(s.presentJson || "[]").length;
          } catch {
            /* ignore */
          }
          return (
            <li key={s.sceneId}>
              <button
                type="button"
                className={`place-card${active ? " place-card--active" : ""}`}
                onClick={() => onSelect(s.sceneId)}
              >
                <span className="place-card__name">{s.locationName}</span>
                {presentCount > 0 && (
                  <span className="place-card__badge" aria-label={`${presentCount} present`}>
                    {presentCount}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </RailSection>
  );
}
