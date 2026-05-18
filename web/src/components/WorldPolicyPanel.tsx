import { useEffect, useState } from "react";
import { api } from "../api/client";

type Props = {
  worldId: string;
};

export function WorldPolicyPanel({ worldId }: Props) {
  const [policy, setPolicy] = useState({
    requireWebToolApproval: false,
    auditWebTools: true,
    pauseCommissionsDuringPersonaDialogue: true,
    citeProvenanceInPrompt: false,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getWorldPolicy(worldId).then((p) =>
      setPolicy({
        requireWebToolApproval: !!p.requireWebToolApproval,
        auditWebTools: p.auditWebTools !== false,
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
        pauseCommissionsDuringPersonaDialogue: next.pauseCommissionsDuringPersonaDialogue !== false,
        citeProvenanceInPrompt: !!next.citeProvenanceInPrompt,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="settings-section">
      <h3>World policy</h3>
      <p className="settings-muted">Per-world orchestration and tool gates (stored in world config).</p>
      <label className="settings-row">
        <input
          type="checkbox"
          checked={policy.requireWebToolApproval}
          disabled={saving}
          onChange={(e) => save({ requireWebToolApproval: e.target.checked })}
        />
        Require approval for web tools
      </label>
      <label className="settings-row">
        <input
          type="checkbox"
          checked={policy.auditWebTools}
          disabled={saving}
          onChange={(e) => save({ auditWebTools: e.target.checked })}
        />
        Audit web tool calls (auto-approve when not required)
      </label>
      <label className="settings-row">
        <input
          type="checkbox"
          checked={policy.pauseCommissionsDuringPersonaDialogue}
          disabled={saving}
          onChange={(e) => save({ pauseCommissionsDuringPersonaDialogue: e.target.checked })}
        />
        Defer commissions during persona dialogue at target scene
      </label>
      <label className="settings-row">
        <input
          type="checkbox"
          checked={policy.citeProvenanceInPrompt}
          disabled={saving}
          onChange={(e) => save({ citeProvenanceInPrompt: e.target.checked })}
        />
        Cite evidence provenance in cast prompts
      </label>
    </section>
  );
}
