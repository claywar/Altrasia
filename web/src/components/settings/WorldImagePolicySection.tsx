import { useEffect, useState } from "react";
import { api, type ImageProfile, type WorldPolicy } from "../../api/client";
import { SettingsBlock } from "./SettingsBlock";

const WORKFLOW_IDS = [
  "character_portrait",
  "scene_establishing",
  "fixture_icon",
  "map_thumbnail",
] as const;

type Props = {
  worldId: string;
};

export function WorldImagePolicySection({ worldId }: Props) {
  const [profiles, setProfiles] = useState<ImageProfile[]>([]);
  const [policy, setPolicy] = useState<Partial<WorldPolicy>>({
    imageUseOperatorDefaults: true,
    requireApprovalForImageGen: false,
    allowCastImageGen: false,
    imageWorkflowProfiles: {},
  });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listImageProfiles().then((r) => setProfiles(r.profiles)).catch(() => setProfiles([]));
    api.getWorldPolicy(worldId).then((p) =>
      setPolicy({
        imageDefaultProfileId: p.imageDefaultProfileId ?? null,
        imageWorkflowProfiles: p.imageWorkflowProfiles ?? {},
        imageUseOperatorDefaults: p.imageUseOperatorDefaults !== false,
        requireApprovalForImageGen: !!p.requireApprovalForImageGen,
        allowCastImageGen: !!p.allowCastImageGen,
      })
    );
  }, [worldId]);

  const save = async (patch: Partial<WorldPolicy>) => {
    setBusy(true);
    try {
      const next = await api.patchWorldPolicy(worldId, patch);
      setPolicy({
        imageDefaultProfileId: next.imageDefaultProfileId ?? null,
        imageWorkflowProfiles: next.imageWorkflowProfiles ?? {},
        imageUseOperatorDefaults: next.imageUseOperatorDefaults !== false,
        requireApprovalForImageGen: !!next.requireApprovalForImageGen,
        allowCastImageGen: !!next.allowCastImageGen,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <SettingsBlock
      title="Image generation policy"
      description="Override operator Media defaults for this world. Falls back to Settings → Media when unset."
    >
      <ul className="settings-list">
        <li className="settings-list-item">
          <label className="settings-list-item-label">
            <input
              type="checkbox"
              checked={policy.imageUseOperatorDefaults !== false}
              disabled={busy}
              onChange={(e) => save({ imageUseOperatorDefaults: e.target.checked })}
            />
            <span className="settings-list-text">Use operator Media defaults</span>
          </label>
        </li>
        <li className="settings-list-item">
          <label className="settings-list-item-label">
            <input
              type="checkbox"
              checked={!!policy.requireApprovalForImageGen}
              disabled={busy}
              onChange={(e) => save({ requireApprovalForImageGen: e.target.checked })}
            />
            <span className="settings-list-text">Require approval for image_generate (IMG-5)</span>
          </label>
        </li>
        <li className="settings-list-item">
          <label className="settings-list-item-label">
            <input
              type="checkbox"
              checked={!!policy.allowCastImageGen}
              disabled={busy}
              onChange={(e) => save({ allowCastImageGen: e.target.checked })}
            />
            <span className="settings-list-text">Allow cast to call image_generate (IMG-7)</span>
          </label>
        </li>
      </ul>
      {policy.imageUseOperatorDefaults === false && (
        <div className="settings-fields">
          <label className="settings-field">
            <span className="settings-field-label">World default profile</span>
            <select
              value={policy.imageDefaultProfileId ?? ""}
              disabled={busy}
              onChange={(e) =>
                save({ imageDefaultProfileId: e.target.value || null })
              }
            >
              <option value="">None</option>
              {profiles.map((p) => (
                <option key={p.profileId} value={p.profileId}>
                  {p.displayName}
                </option>
              ))}
            </select>
          </label>
          {WORKFLOW_IDS.map((wf) => (
            <label key={wf} className="settings-field">
              <span className="settings-field-label">{wf.replace(/_/g, " ")}</span>
              <select
                value={policy.imageWorkflowProfiles?.[wf] ?? ""}
                disabled={busy}
                onChange={(e) => {
                  const wfMap = { ...(policy.imageWorkflowProfiles ?? {}) };
                  if (e.target.value) wfMap[wf] = e.target.value;
                  else delete wfMap[wf];
                  save({ imageWorkflowProfiles: wfMap });
                }}
              >
                <option value="">Inherit</option>
                {profiles
                  .filter((p) => p.supportedWorkflows.includes(wf))
                  .map((p) => (
                    <option key={p.profileId} value={p.profileId}>
                      {p.displayName}
                    </option>
                  ))}
              </select>
            </label>
          ))}
        </div>
      )}
    </SettingsBlock>
  );
}
