import { Button } from "../../ui/Button";
import { RailSection } from "../../ui/RailSection";

export type ExitItem = {
  exitId: string;
  label: string;
  targetSceneId: string;
  direction?: string;
};

type Props = {
  exits: ExitItem[];
  highlightedExitId: string | null;
  onTravel: (targetSceneId: string) => void;
  onKnock: (targetSceneId: string) => void;
  onExitHover: (exitId: string | null) => void;
};

const DIR_GLYPH: Record<string, string> = {
  N: "↑",
  NE: "↗",
  E: "→",
  SE: "↘",
  S: "↓",
  SW: "↙",
  W: "←",
  NW: "↖",
};

export function ExitList({ exits, highlightedExitId, onTravel, onKnock, onExitHover }: Props) {
  return (
    <RailSection title="Exits" testId="exit-list">
      <ul className="exit-list">
        {exits.length === 0 && <li className="exit-list__empty">No exits from here</li>}
        {exits.map((ex) => (
          <li
            key={ex.exitId}
            className={`exit-card${highlightedExitId === ex.exitId ? " exit-card--highlight" : ""}`}
            onMouseEnter={() => onExitHover(ex.exitId)}
            onMouseLeave={() => onExitHover(null)}
            onFocus={() => onExitHover(ex.exitId)}
            onBlur={() => onExitHover(null)}
          >
            <button type="button" className="exit-card__main" onClick={() => onTravel(ex.targetSceneId)}>
              {ex.direction && (
                <span className="exit-card__dir" aria-hidden>
                  {DIR_GLYPH[ex.direction] ?? "·"}
                </span>
              )}
              <span className="exit-card__label">{ex.label}</span>
            </button>
            <Button variant="ghost" size="sm" onClick={() => onKnock(ex.targetSceneId)}>
              Knock
            </Button>
          </li>
        ))}
      </ul>
    </RailSection>
  );
}
