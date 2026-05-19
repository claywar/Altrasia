import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { SettingsBlock } from "./SettingsBlock";

type Props = {
  worldId: string;
};

export function IdleSocialPolicySection({ worldId }: Props) {
  const [idleBanterEnabled, setIdleBanterEnabled] = useState(true);
  const [cooldownSeconds, setCooldownSeconds] = useState(120);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getWorldPolicy(worldId).then((p) => {
      setIdleBanterEnabled(p.idleBanterEnabled !== false);
      const raw = p.operatorInteractionCooldownSeconds;
      setCooldownSeconds(typeof raw === "number" && raw >= 0 ? raw : 120);
    });
  }, [worldId]);

  const save = async (patch: {
    idleBanterEnabled?: boolean;
    operatorInteractionCooldownSeconds?: number;
  }) => {
    setSaving(true);
    try {
      const next = await api.patchWorldPolicy(worldId, patch);
      setIdleBanterEnabled(next.idleBanterEnabled !== false);
      const raw = next.operatorInteractionCooldownSeconds;
      setCooldownSeconds(typeof raw === "number" && raw >= 0 ? raw : 120);
    } finally {
      setSaving(false);
    }
  };

  return (
    <SettingsBlock
      title="Idle & banter"
      description="Control sidebar banter and GPU-friendly quiet periods after you speak in-scene."
    >
      <ul className="settings-list">
        <li className="settings-list-item">
          <label className="settings-list-item-label">
            <span className="settings-list-text">
              Enable banter turns
              <span className="settings-list-hint">
                Dyad sidebar chat between NPCs; turn off while debugging
              </span>
            </span>
            <input
              type="checkbox"
              className="settings-toggle"
              checked={idleBanterEnabled}
              disabled={saving}
              onChange={(e) => save({ idleBanterEnabled: e.target.checked })}
            />
          </label>
        </li>
        <li className="settings-list-item">
          <label className="settings-field settings-field-inline">
            <span className="settings-field-label">
              Operator quiet period (seconds)
              <span className="settings-list-hint">
                After you send a line, block banter and solo idle ticks for this long
              </span>
            </span>
            <input
              type="number"
              min={0}
              max={3600}
              step={15}
              value={cooldownSeconds}
              disabled={saving}
              onChange={(e) => setCooldownSeconds(Number(e.target.value))}
              onBlur={() =>
                save({
                  operatorInteractionCooldownSeconds: Math.max(0, cooldownSeconds),
                })
              }
            />
          </label>
        </li>
      </ul>
    </SettingsBlock>
  );
}
