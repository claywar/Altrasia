import { useCallback, useEffect, useState } from "react";
import { api, type CastCharacter, type WebToolsAccess, type WorldPolicy } from "../api/client";
import {
  effectiveWebToolsAccess,
  WEB_ACCESS_OPTIONS,
  webAccessOptionLabel,
} from "../lib/webToolsAccess";
import { SettingsBlock } from "./settings/SettingsBlock";

type Props = {
  worldId: string;
  embedded?: boolean;
};

export function CastListPanel({ worldId, embedded }: Props) {
  const [cast, setCast] = useState<CastCharacter[]>([]);
  const [policy, setPolicy] = useState<WorldPolicy | undefined>();
  const [savingId, setSavingId] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([api.listCharacters(worldId), api.getWorldPolicy(worldId)])
      .then(([chars, p]) => {
        setCast(chars);
        setPolicy(p);
      })
      .catch(() => {
        setCast([]);
        setPolicy(undefined);
      });
  }, [worldId]);

  useEffect(() => {
    load();
  }, [load]);

  const saveWebAccess = async (characterId: string, webToolsAccess: WebToolsAccess) => {
    setSavingId(characterId);
    try {
      await api.patchCharacter(characterId, { definition: { webToolsAccess } });
      load();
    } finally {
      setSavingId(null);
    }
  };

  const callout = (
    <p className="settings-block-desc cast-web-callout">
      Characters cannot search the web until Web tools is not Off. Leadership roles may
      default to Ask via world policy.
    </p>
  );

  const list = (
    <ul className="settings-list settings-list-plain">
      {cast.map((c) => {
        const { access, fromRoleDefault } = effectiveWebToolsAccess(
          c.definition,
          c.sceneRole,
          policy
        );
        const stored = c.definition?.webToolsAccess;
        const selectValue = stored ?? access;
        return (
          <li key={c.characterId} className="settings-list-item cast-list-item">
            <div className="settings-list-text">
              <strong>{c.displayName}</strong>
              {c.muted ? " (muted)" : ""}
              {c.disabled ? " (disabled)" : ""}
              <span className="settings-list-meta">{c.characterId.replace("char-", "")}</span>
            </div>
            <label className="cast-web-access">
              <span className="settings-muted">Web tools</span>
              <select
                value={selectValue}
                disabled={savingId === c.characterId}
                onChange={(e) =>
                  saveWebAccess(c.characterId, e.target.value as WebToolsAccess)
                }
                aria-label={`Web tools access for ${c.displayName}`}
              >
                {WEB_ACCESS_OPTIONS.map((opt) => (
                  <option
                    key={opt.value}
                    value={opt.value}
                    title={opt.hint}
                  >
                    {opt.value === access && fromRoleDefault && stored === undefined
                      ? webAccessOptionLabel(opt.value, true)
                      : opt.label}
                  </option>
                ))}
              </select>
            </label>
          </li>
        );
      })}
      {cast.length === 0 && (
        <li className="settings-list-item settings-list-empty">No cast yet</li>
      )}
    </ul>
  );

  if (embedded) {
    return (
      <SettingsBlock
        title="Cast"
        description="Per-character web tool access. Allowed skips approval even when the world requires it."
      >
        {callout}
        {list}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section">
      <h3>Cast</h3>
      <p className="settings-muted">
        {cast.length} character(s). Configure web tools per character below.
      </p>
      {callout}
      {list}
    </section>
  );
}
