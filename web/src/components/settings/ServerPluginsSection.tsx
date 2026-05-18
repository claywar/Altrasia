import { useState } from "react";
import { api, type OperatorSettings } from "../../api/client";
import { SettingsBlock } from "./SettingsBlock";

type Props = {
  settings: OperatorSettings;
  onUpdated: (next: OperatorSettings) => void;
};

export function ServerPluginsSection({ settings, onUpdated }: Props) {
  const [busy, setBusy] = useState(false);

  return (
    <SettingsBlock title="Server plugins" description="Optional server-side plugin hooks.">
      <ul className="settings-list">
        <li className="settings-list-item">
          <label className="settings-list-item-label">
            <span className="settings-list-text">Enable server plugins</span>
            <input
              type="checkbox"
              className="settings-toggle"
              checked={!!settings.enableServerPlugins}
              disabled={busy}
              onChange={async (e) => {
                setBusy(true);
                try {
                  const next = await api.patchOperatorSettings({
                    enableServerPlugins: e.target.checked,
                  });
                  onUpdated(next);
                } finally {
                  setBusy(false);
                }
              }}
            />
          </label>
        </li>
      </ul>
    </SettingsBlock>
  );
}
