type Props = {
  compact?: boolean;
};

export function LevelStackLegend({ compact = false }: Props) {
  return (
    <div
      className={`level-stack-legend${compact ? " level-stack-legend--compact" : ""}`}
      aria-label="Stack legend"
    >
      {!compact && <h4>Legend</h4>}
      <ul>
        <li>
          <span className="level-stack-legend__icon level-stack-legend__icon--stairs" aria-hidden>
            ▲
          </span>
          <span>
            {compact ? "Stairs" : (
              <>
                <strong>STAIRS</strong> — move between floors
              </>
            )}
          </span>
        </li>
        <li>
          <span className="level-stack-legend__icon level-stack-legend__icon--ladder" aria-hidden>
            ▼
          </span>
          <span>
            {compact ? "Ladder" : (
              <>
                <strong>LADDER</strong> — vertical shaft access
              </>
            )}
          </span>
        </li>
        {!compact && (
          <li>
            <span className="level-stack-legend__dot" aria-hidden />
            <span>
              <strong>YOU ARE HERE</strong> — active scene
            </span>
          </li>
        )}
      </ul>
    </div>
  );
}
