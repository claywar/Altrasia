import { useState } from "react";
import { api } from "../../api/client";
import { SettingsBlock } from "./SettingsBlock";

type Props = {
  worldId: string;
  onReset: () => void | Promise<void>;
};

export function DemoResetSection({ worldId, onReset }: Props) {
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  return (
    <SettingsBlock
      title="Vertex Labs demo reset"
      description="Restore the HQ demo to its initial configuration. Clears all chat, diary entries, and memories added during play."
    >
      {!confirming ? (
        <ul className="settings-list settings-list-actions">
          <li className="settings-list-item">
            <span className="settings-list-text">Clean slate for repeated tests</span>
            <button
              type="button"
              disabled={busy}
              data-testid="demo-reset-open"
              onClick={() => setConfirming(true)}
            >
              Reset demo
            </button>
          </li>
        </ul>
      ) : (
        <div className="settings-block-callout">
          <p>
            This cannot be undone. Export a world package first if you need a backup.
          </p>
          <ul className="settings-list settings-list-actions">
            <li className="settings-list-item">
              <span className="settings-list-text">Confirm reset</span>
              <button
                type="button"
                disabled={busy}
                data-testid="demo-reset-confirm"
                onClick={async () => {
                  setBusy(true);
                  try {
                    await api.resetDemoFixture(worldId);
                    await onReset();
                    setConfirming(false);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {busy ? "Resetting…" : "Yes, reset"}
              </button>
            </li>
            <li className="settings-list-item">
              <span className="settings-list-text">Keep current state</span>
              <button type="button" disabled={busy} onClick={() => setConfirming(false)}>
                Cancel
              </button>
            </li>
          </ul>
        </div>
      )}
    </SettingsBlock>
  );
}
