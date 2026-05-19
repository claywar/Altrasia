import { useCallback, useState } from "react";
import { api, type LayoutDraft, type SpatialGraph } from "../../api/client";
import { LayoutDraftPreview } from "../maps/LayoutDraftPreview";
import { mergeDraftToGraph } from "../maps/layoutDraftMerge";

type Props = {
  worldId: string;
  graph: SpatialGraph | null;
  onCommitted?: () => void;
  onPreviewChange?: (preview: SpatialGraph | null) => void;
};

export function MapEnhancePanel({ worldId, graph, onCommitted, onPreviewChange }: Props) {
  const [brief, setBrief] = useState("");
  const [draft, setDraft] = useState<LayoutDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [jsonText, setJsonText] = useState("");
  const [repairText, setRepairText] = useState("");

  const syncPreview = useCallback(
    (d: LayoutDraft | null) => {
      if (!d?.proposed || !graph) {
        onPreviewChange?.(null);
        return;
      }
      onPreviewChange?.(mergeDraftToGraph(d.proposed, graph));
    },
    [graph, onPreviewChange]
  );

  const syncJsonFromDraft = useCallback(
    (d: LayoutDraft | null) => {
      if (d?.proposed) setJsonText(JSON.stringify(d.proposed, null, 2));
      syncPreview(d);
    },
    [syncPreview]
  );

  return (
    <div className="map-enhance-panel" data-testid="map-enhance-panel">
      <p className="map-enhance-panel__lead">
        Describe how rooms and buildings should be arranged. We generate and validate the full layout for you.
      </p>
      <textarea
        className="char-draft-brief"
        value={brief}
        onChange={(e) => setBrief(e.target.value)}
        placeholder="e.g. Hall west, kitchen north-east, manor envelope around both…"
        rows={3}
      />
      <div className="map-enhance-panel__actions">
        <button
          type="button"
          disabled={busy || !brief.trim()}
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              const d = await api.createUnifiedLayoutDraft(worldId, { brief: brief.trim() });
              setDraft(d);
              syncJsonFromDraft(d);
            } catch (e) {
              setError(e instanceof Error ? e.message : "Generate failed");
              onPreviewChange?.(null);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Generating…" : "Generate"}
        </button>
        {draft?.status === "ready" && (
          <>
            <button
              type="button"
              className="map-enhance-panel__primary"
              disabled={busy || draft.validation?.valid === false}
              onClick={async () => {
                setBusy(true);
                setError(null);
                try {
                  await api.commitLayoutDraft(worldId, draft.layoutDraftId);
                  setDraft(null);
                  setBrief("");
                  onPreviewChange?.(null);
                  onCommitted?.();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Apply failed");
                } finally {
                  setBusy(false);
                }
              }}
            >
              Use this layout
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setDraft(null);
                setJsonText("");
                onPreviewChange?.(null);
              }}
            >
              Discard
            </button>
          </>
        )}
      </div>

      {error && <p className="settings-error">{error}</p>}

      {draft?.status === "ready" && (
        <>
          <LayoutDraftPreview scope={draft.scope ?? "unified"} draft={draft} baseGraph={graph} />
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
        </>
      )}

      <button
        type="button"
        className="map-enhance-panel__advanced-toggle"
        onClick={() => setAdvancedOpen((v) => !v)}
      >
        {advancedOpen ? "Hide advanced" : "Advanced (JSON & repair)"}
      </button>
      {advancedOpen && draft?.status === "ready" && (
        <div className="map-enhance-panel__advanced">
          <textarea
            className="map-draft-json"
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            rows={10}
          />
          <button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                const proposed = JSON.parse(jsonText);
                const updated = await api.patchLayoutDraft(worldId, draft.layoutDraftId, proposed);
                setDraft(updated);
                syncJsonFromDraft(updated);
              } catch (e) {
                setError(e instanceof Error ? e.message : "Invalid JSON");
              } finally {
                setBusy(false);
              }
            }}
          >
            Sync JSON
          </button>
          <div className="map-draft-repair">
            <input
              type="text"
              value={repairText}
              onChange={(e) => setRepairText(e.target.value)}
              placeholder="Describe a fix…"
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
        </div>
      )}
    </div>
  );
}
