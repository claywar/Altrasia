import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { SettingsBlock } from "./SettingsBlock";

type Props = {
  worldId: string;
};

export function ReflectionPolicySection({ worldId }: Props) {
  const [enabled, setEnabled] = useState(false);
  const [nightlyHour, setNightlyHour] = useState(3);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getWorldPolicy(worldId).then((p) => {
      setEnabled(p.reflectionEnabled === true);
      setNightlyHour(p.reflectionNightlyHourUtc ?? 3);
    });
  }, [worldId]);

  const save = async (patch: {
    reflectionEnabled?: boolean;
    reflectionNightlyHourUtc?: number;
  }) => {
    setSaving(true);
    try {
      const next = await api.patchWorldPolicy(worldId, patch);
      setEnabled(next.reflectionEnabled === true);
      setNightlyHour(next.reflectionNightlyHourUtc ?? 3);
    } finally {
      setSaving(false);
    }
  };

  return (
    <SettingsBlock
      title="Character reflection"
      description="Nightly consolidation of diary into beliefs, memory links, and optional persona proposals."
    >
      <ul className="settings-list">
        <li className="settings-list-item">
          <label className="settings-list-item-label">
            <span className="settings-list-text">Enable nightly reflection</span>
            <input
              type="checkbox"
              className="settings-toggle"
              checked={enabled}
              disabled={saving}
              onChange={(e) => save({ reflectionEnabled: e.target.checked })}
            />
          </label>
        </li>
        <li className="settings-list-item">
          <label className="settings-list-item-label">
            <span className="settings-list-text">
              Nightly hour (UTC)
              <span className="settings-list-hint">Batch runs when GPU is idle</span>
            </span>
            <input
              type="number"
              min={0}
              max={23}
              className="settings-number-input"
              value={nightlyHour}
              disabled={saving}
              onChange={(e) => {
                const v = Math.min(23, Math.max(0, parseInt(e.target.value, 10) || 0));
                setNightlyHour(v);
                save({ reflectionNightlyHourUtc: v });
              }}
            />
          </label>
        </li>
      </ul>
    </SettingsBlock>
  );
}
