import { useEffect, useRef, useState } from "react";
import { api, type OperatorSettings } from "../../api/client";
import { SettingsBlock } from "./SettingsBlock";

type Props = {
  settings: OperatorSettings;
  onUpdated: (next: OperatorSettings) => void;
};

export function ServerHeartbeatSection({ settings, onUpdated }: Props) {
  const [busy, setBusy] = useState(false);
  const [intervalSeconds, setIntervalSeconds] = useState(settings.heartbeat.intervalSeconds);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setIntervalSeconds(settings.heartbeat.intervalSeconds);
  }, [settings.heartbeat.intervalSeconds]);

  const patchHeartbeat = async (patch: { enabled?: boolean; intervalSeconds?: number }) => {
    setBusy(true);
    try {
      const next = await api.patchOperatorSettings({ heartbeat: patch });
      onUpdated(next);
    } finally {
      setBusy(false);
    }
  };

  const scheduleIntervalSave = (value: number) => {
    setIntervalSeconds(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      patchHeartbeat({ intervalSeconds: value });
    }, 400);
  };

  useEffect(
    () => () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    },
    []
  );

  return (
    <SettingsBlock
      title="Server heartbeat"
      description="NPC idle rotation when no browser tab is connected."
    >
      <ul className="settings-list">
        <li className="settings-list-item">
          <label className="settings-list-item-label">
            <span className="settings-list-text">Enable server heartbeat</span>
            <input
              type="checkbox"
              className="settings-toggle"
              checked={settings.heartbeat.enabled}
              disabled={busy}
              onChange={(e) => patchHeartbeat({ enabled: e.target.checked })}
            />
          </label>
        </li>
        <li className="settings-list-item">
          <div className="settings-list-field">
            <span className="settings-list-text">Interval (seconds)</span>
            <input
              type="number"
              className="settings-input-narrow"
              min={5}
              value={intervalSeconds}
              disabled={busy}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10) || 60;
                scheduleIntervalSave(Math.max(5, v));
              }}
            />
          </div>
        </li>
      </ul>
      {settings.lastHeartbeatAt && (
        <p className="settings-block-foot">Last tick: {settings.lastHeartbeatAt}</p>
      )}
    </SettingsBlock>
  );
}
