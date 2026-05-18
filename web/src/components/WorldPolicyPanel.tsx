import { useEffect, useState } from "react";
import { api } from "../api/client";
import { SettingsBlock } from "./settings/SettingsBlock";

const policyDefaults = {
  requireWebToolApproval: false,
  auditWebTools: true,
  webToolsMock: true,
  pauseCommissionsDuringPersonaDialogue: true,
  citeProvenanceInPrompt: false,
};

const POLICY_ITEMS: Array<{
  key: keyof typeof policyDefaults;
  label: string;
  hint?: string;
}> = [
  { key: "requireWebToolApproval", label: "Require approval for web tools" },
  {
    key: "auditWebTools",
    label: "Audit web tool calls",
    hint: "Auto-approve when approval not required",
  },
  {
    key: "webToolsMock",
    label: "Use mock web fetch",
    hint: "Disable for live allowlisted fetch",
  },
  {
    key: "pauseCommissionsDuringPersonaDialogue",
    label: "Defer commissions during persona dialogue",
  },
  { key: "citeProvenanceInPrompt", label: "Cite evidence provenance in cast prompts" },
];

type Props = {
  worldId: string;
  embedded?: boolean;
};

export function WorldPolicyPanel({ worldId, embedded }: Props) {
  const [policy, setPolicy] = useState({ ...policyDefaults });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getWorldPolicy(worldId).then((p) =>
      setPolicy({
        requireWebToolApproval: !!p.requireWebToolApproval,
        auditWebTools: p.auditWebTools !== false,
        webToolsMock: p.webToolsMock !== false,
        pauseCommissionsDuringPersonaDialogue: p.pauseCommissionsDuringPersonaDialogue !== false,
        citeProvenanceInPrompt: !!p.citeProvenanceInPrompt,
      })
    );
  }, [worldId]);

  const save = async (patch: Partial<typeof policy>) => {
    setSaving(true);
    try {
      const next = await api.patchWorldPolicy(worldId, patch);
      setPolicy({
        requireWebToolApproval: !!next.requireWebToolApproval,
        auditWebTools: next.auditWebTools !== false,
        webToolsMock: next.webToolsMock !== false,
        pauseCommissionsDuringPersonaDialogue: next.pauseCommissionsDuringPersonaDialogue !== false,
        citeProvenanceInPrompt: !!next.citeProvenanceInPrompt,
      });
    } finally {
      setSaving(false);
    }
  };

  const list = (
    <ul className="settings-list">
      {POLICY_ITEMS.map((item) => (
        <li key={item.key} className="settings-list-item">
          <label className="settings-list-item-label">
            <span className="settings-list-text">
              {item.label}
              {item.hint && <span className="settings-list-hint">{item.hint}</span>}
            </span>
            <input
              type="checkbox"
              className="settings-toggle"
              checked={policy[item.key]}
              disabled={saving}
              onChange={(e) => save({ [item.key]: e.target.checked } as Partial<typeof policy>)}
            />
          </label>
        </li>
      ))}
    </ul>
  );

  if (embedded) {
    return (
      <SettingsBlock title="World policy" description="Orchestration and tool gates for this world.">
        {list}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section">
      <h3>World policy</h3>
      <p className="settings-muted">Per-world orchestration and tool gates (stored in world config).</p>
      {list}
    </section>
  );
}
