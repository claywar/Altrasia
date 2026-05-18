import { useCallback, useState } from "react";
import { api, type LayoutDraft, type SpatialGraph } from "../api/client";
import { LayoutDraftPreview } from "../features/maps/LayoutDraftPreview";
import { SettingsBlock } from "./settings/SettingsBlock";

type Props = {
  worldId: string;
  graph?: SpatialGraph | null;
  onCommitted?: () => void;
  embedded?: boolean;
};

type Tab = "visual" | "json";

export function MapDraftPanel({ worldId, graph, onCommitted, embedded }: Props) {
  const [brief, setBrief] = useState("");
  const [scope, setScope] = useState("mini");
  const [draft, setDraft] = useState<LayoutDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("visual");
  const [jsonText, setJsonText] = useState("");
  const [repairText, setRepairText] = useState("");
  const [cascadeOffer, setCascadeOffer] = useState<string | null>(null);

  const syncJsonFromDraft = useCallback((d: LayoutDraft | null) => {
    if (d?.proposed) setJsonText(JSON.stringify(d.proposed, null, 2));
  }, []);

  const body = (
    <>
      <div className="map-draft-controls">
        <label>
          Scope
          <select value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="mini">Mini</option>
            <option value="site">Site</option>
            <option value="stack">Stack</option>
            <option value="floor">Floor</option>
          </select>
        </label>
      </div>
      <textarea
        className="char-draft-brief"
        value={brief}
        onChange={(e) => setBrief(e.target.value)}
        placeholder="e.g. Hall left, kitchen north, manor envelope around both rooms…"
        rows={3}
      />
      <div className="settings-inline-actions">
        <button
          type="button"
          disabled={busy || !brief.trim()}
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              const d = await api.createLayoutDraft(worldId, {
                brief: brief.trim(),
                scope,
              });
              setDraft(d);
              syncJsonFromDraft(d);
            } catch (e) {
              setError(e instanceof Error ? e.message : "Draft failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          Generate draft
        </button>
        {draft?.status === "ready" && (
          <>
            <button
              type="button"
              disabled={busy || draft.validation?.valid === false}
              title={
                draft.validation?.valid === false
                  ? "Fix validation errors before commit"
                  : undefined
              }
              onClick={async () => {
                setBusy(true);
                setError(null);
                try {
                  await api.commitLayoutDraft(worldId, draft.layoutDraftId);
                  const nextScope =
                    scope === "mini" ? "site" : scope === "site" ? "stack" : null;
                  setDraft(null);
                  setBrief("");
                  onCommitted?.();
                  if (nextScope) setCascadeOffer(nextScope);
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Commit failed");
                } finally {
                  setBusy(false);
                }
              }}
            >
              Commit layout
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setDraft(null);
                setJsonText("");
              }}
            >
              Discard
            </button>
          </>
        )}
      </div>

      {cascadeOffer && (
        <p className="map-draft-cascade">
          Layout committed.{" "}
          <button
            type="button"
            onClick={() => {
              setScope(cascadeOffer);
              setCascadeOffer(null);
              setBrief(`Enhance ${cascadeOffer} layout for this world`);
            }}
          >
            Generate {cascadeOffer} layout?
          </button>
          <button type="button" onClick={() => setCascadeOffer(null)}>
            Skip
          </button>
        </p>
      )}

      {error && <p className="settings-error">{error}</p>}

      {draft?.status === "ready" && (
        <>
          <div className="map-draft-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={tab === "visual"}
              onClick={() => setTab("visual")}
            >
              Visual
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "json"}
              onClick={() => setTab("json")}
            >
              JSON
            </button>
          </div>

          {tab === "visual" && (
            <LayoutDraftPreview scope={scope} draft={draft} baseGraph={graph ?? null} />
          )}

          {draft.validation?.errors?.length ? (
            <ul className="map-draft-validation map-draft-validation--errors">
              {draft.validation.errors.map((msg) => (
                <li key={msg}>{msg}</li>
              ))}
            </ul>
          ) : null}
          {draft.validation?.warnings?.length ? (
            <ul className="map-draft-validation map-draft-validation--warnings">
              {draft.validation.warnings.map((msg) => (
                <li key={msg}>{msg}</li>
              ))}
            </ul>
          ) : null}

          {tab === "json" && (
            <>
              <textarea
                className="map-draft-json"
                value={jsonText}
                onChange={(e) => setJsonText(e.target.value)}
                rows={12}
              />
              <button
                type="button"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError(null);
                  try {
                    const proposed = JSON.parse(jsonText);
                    const updated = await api.patchLayoutDraft(
                      worldId,
                      draft.layoutDraftId,
                      proposed
                    );
                    setDraft(updated);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Invalid JSON");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Sync JSON to preview
              </button>
            </>
          )}

          <div className="map-draft-repair">
            <input
              type="text"
              value={repairText}
              onChange={(e) => setRepairText(e.target.value)}
              placeholder="Describe a change to repair…"
            />
            <button
              type="button"
              disabled={busy || !repairText.trim()}
              onClick={async () => {
                setBusy(true);
                setError(null);
                try {
                  const d = await api.repairLayoutDraft(
                    worldId,
                    draft.layoutDraftId,
                    repairText.trim()
                  );
                  setDraft(d);
                  syncJsonFromDraft(d);
                  setRepairText("");
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Repair failed");
                } finally {
                  setBusy(false);
                }
              }}
            >
              Repair
            </button>
          </div>
        </>
      )}
    </>
  );

  if (embedded) {
    return (
      <SettingsBlock
        title="Map layout"
        description="Generate layout via LLM; edit visually or as JSON; commit applies to world."
      >
        {body}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section map-draft-panel">
      <h3>Map layout (MapDraft)</h3>
      <p className="settings-muted">
        Propose and refine map layouts; commit writes positions, structures, and exit hints.
      </p>
      {body}
    </section>
  );
}
