import { useEffect, useState } from "react";
import { api, type OperatorSettings } from "../api/client";

type Props = {
  worldId: string;
  worldPaused: boolean;
  onClose: () => void;
  onWorldPauseChange: () => void;
};

export function SettingsPanel({
  worldId,
  worldPaused,
  onClose,
  onWorldPauseChange,
}: Props) {
  const [settings, setSettings] = useState<OperatorSettings | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.operatorSettings().then(setSettings);
  }, []);

  const saveHeartbeat = async (patch: { enabled?: boolean; intervalSeconds?: number }) => {
    setSaving(true);
    try {
      const next = await api.patchOperatorSettings({ heartbeat: patch });
      setSettings(next);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-overlay" role="dialog" aria-label="Server settings">
      <div className="settings-panel">
        <header className="settings-header">
          <h2>Settings</h2>
          <button type="button" onClick={onClose}>
            Close
          </button>
        </header>
        <section className="settings-section">
          <h3>This world</h3>
          <p className="settings-muted">
            {worldPaused ? "World is paused — no generation." : "World is active."}
          </p>
          <button
            type="button"
            disabled={saving}
            onClick={async () => {
              if (worldPaused) await api.resumeWorld(worldId);
              else await api.pauseWorld(worldId);
              onWorldPauseChange();
            }}
          >
            {worldPaused ? "Resume world" : "Pause world"}
          </button>
        </section>
        <section className="settings-section">
          <h3>Global heartbeat (v1.1)</h3>
          <p className="settings-muted">
            NPC idle rotation when no browser tab is connected. Tab-visible idle still runs
            while this page is open.
          </p>
          {settings && (
            <>
              <label className="settings-row">
                <input
                  type="checkbox"
                  checked={settings.heartbeat.enabled}
                  onChange={(e) => saveHeartbeat({ enabled: e.target.checked })}
                />
                Enable server heartbeat
              </label>
              <label className="settings-row">
                Interval (seconds)
                <input
                  type="number"
                  min={5}
                  value={settings.heartbeat.intervalSeconds}
                  onChange={(e) =>
                    saveHeartbeat({ intervalSeconds: parseInt(e.target.value, 10) || 60 })
                  }
                />
              </label>
              {settings.lastHeartbeatAt && (
                <p className="settings-muted">Last tick: {settings.lastHeartbeatAt}</p>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
