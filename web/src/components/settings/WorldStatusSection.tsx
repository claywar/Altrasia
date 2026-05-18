type Props = {
  worldPaused: boolean;
};

export function WorldStatusSection({ worldPaused }: Props) {
  return (
    <div className="settings-block settings-block-compact">
      <div className="settings-status-row">
        <span className={`settings-status-pill${worldPaused ? " paused" : ""}`}>
          {worldPaused ? "Paused" : "Active"}
        </span>
        <span className="settings-status-hint">Pause or Resume from the toolbar</span>
      </div>
    </div>
  );
}
