import { useState } from "react";
import type { World } from "../api/client";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

type Props = {
  loading: boolean;
  savedWorlds: World[];
  onLoadDemo: () => void;
  onCreateArchitect: () => void;
  onOpenWorld: (w: World) => void;
};

export function LauncherView({
  loading,
  savedWorlds,
  onLoadDemo,
  onCreateArchitect,
  onOpenWorld,
}: Props) {
  const [helpOpen, setHelpOpen] = useState(false);

  return (
    <div className="launcher" data-testid="launcher">
      <div className="launcher__poster">
        <div className="launcher__glow" aria-hidden />
        <h1 className="launcher__title">Altrasia</h1>
        <p className="launcher__tagline">
          Persistent stage for AI characters — memory-grounded, spatial, operator-run.
        </p>
      </div>
      <div className="launcher__actions">
        <Button variant="primary" onClick={onLoadDemo} disabled={loading} className="launcher__cta">
          {loading ? "Loading…" : "Load demo world"}
        </Button>
        <Button variant="ghost" onClick={onCreateArchitect} disabled={loading}>
          New world (Architect)
        </Button>
      </div>
      <p className="launcher__hint">
        Demo: Hall + Kitchen · Architect: add scenes in Settings, then lock geography
      </p>
      <button
        type="button"
        className="launcher__help-toggle"
        aria-expanded={helpOpen}
        onClick={() => setHelpOpen((v) => !v)}
      >
        {helpOpen ? "Hide first session tips" : "First session tips"}
      </button>
      {helpOpen && (
        <ol className="launcher__steps">
          <li>Load demo → public line in Hall (Alice replies)</li>
          <li>Whisper Alice · switch to Kitchen · knock on exit</li>
          <li>Observer Studio · Settings: commissions, MapDraft, debate</li>
          <li>Pause/Resume in top bar · export world package</li>
        </ol>
      )}
      {savedWorlds.length > 0 && (
        <div className="launcher__saved">
          <h2>Resume a world</h2>
          <ul className="launcher__world-cards">
            {savedWorlds.map((w) => (
              <li key={w.worldId}>
                <Card className="launcher__world-card">
                  <button
                    type="button"
                    className="launcher__world-btn"
                    disabled={loading}
                    onClick={() => onOpenWorld(w)}
                  >
                    <span className="launcher__world-name">{w.name}</span>
                  </button>
                </Card>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
