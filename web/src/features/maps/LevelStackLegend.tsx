export function LevelStackLegend() {
  return (
    <div className="level-stack-legend" aria-label="Stack legend">
      <h4>Legend</h4>
      <ul>
        <li>
          <span className="level-stack-legend__icon level-stack-legend__icon--stairs" aria-hidden>
            ▲
          </span>
          <span>
            <strong>STAIRS</strong> — move between floors
          </span>
        </li>
        <li>
          <span className="level-stack-legend__icon level-stack-legend__icon--ladder" aria-hidden>
            ▼
          </span>
          <span>
            <strong>LADDER</strong> — vertical shaft access
          </span>
        </li>
        <li>
          <span className="level-stack-legend__dot" aria-hidden />
          <span>
            <strong>YOU ARE HERE</strong> — active scene
          </span>
        </li>
      </ul>
    </div>
  );
}
