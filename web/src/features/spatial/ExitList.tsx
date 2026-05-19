import { Button } from "../../ui/Button";
import { RailSection } from "../../ui/RailSection";
import { exitKnockAffordance, type ExitRow } from "./exitAffordances";

export type ExitItem = ExitRow;

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

type Props = {
  exits: ExitItem[];
  highlightedExitId: string | null;
  pendingKnockTargetIds?: Set<string>;
  onTravel: (targetSceneId: string) => void;
  onKnock: (targetSceneId: string) => void;
  onExitHover: (exitId: string | null) => void;
};

export function ExitList({
  exits,
  highlightedExitId,
  pendingKnockTargetIds,
  onTravel,
  onKnock,
  onExitHover,
}: Props) {
  return (
    <RailSection title="Exits" testId="exit-list" className="exit-list-section">
      <ul className="exit-list">
        {exits.length === 0 && <li className="exit-list__empty">No exits from here</li>}
        {exits.map((ex) => {
          const affordance = exitKnockAffordance(ex, pendingKnockTargetIds);
          return (
            <li
              key={ex.exitId}
              className={`exit-card${highlightedExitId === ex.exitId ? " exit-card--highlight" : ""}`}
              onMouseEnter={() => onExitHover(ex.exitId)}
              onMouseLeave={() => onExitHover(null)}
              onFocus={() => onExitHover(ex.exitId)}
              onBlur={() => onExitHover(null)}
            >
              <span className="exit-card__dir" aria-hidden>
                {ex.direction ? (DIR_GLYPH[ex.direction] ?? "·") : "·"}
              </span>
              <button
                type="button"
                className="exit-card__main"
                onClick={() => onTravel(ex.targetSceneId)}
                aria-label={`Go to ${ex.label}`}
              >
                <span className="exit-card__label">{ex.label}</span>
              </button>
              <div className="exit-card__action">
                {affordance.showKnock ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={affordance.disabled}
                    onClick={() => onKnock(ex.targetSceneId)}
                    aria-label={`Knock on ${ex.label}`}
                  >
                    {affordance.label}
                  </Button>
                ) : affordance.statusChip ? (
                  <span className="exit-card__status" aria-label={`Door ${affordance.statusChip}`}>
                    {affordance.statusChip}
                  </span>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </RailSection>
  );
}
