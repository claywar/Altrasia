import { useCallback, useEffect, useState } from "react";
import {
  api,
  type InferenceModelList,
  type OperatorSettings,
} from "../../api/client";
import { SettingsBlock } from "./SettingsBlock";

type Props = {
  settings: OperatorSettings;
  onUpdated: (next: OperatorSettings) => void;
};

type Target = "primary" | "embedding";

function envHint(settings: OperatorSettings, key: keyof NonNullable<OperatorSettings["envDefaults"]>) {
  const v = settings.envDefaults?.[key];
  if (v === undefined || v === null || v === "") return "Not set in environment";
  return String(v);
}

export function ServerInferenceSection({ settings, onUpdated }: Props) {
  const [draft, setDraft] = useState(
    settings.inference ?? {
      primaryBaseUrl: "",
      primaryModel: "",
      embeddingBaseUrl: "",
      embeddingModel: "",
    }
  );
  const [busy, setBusy] = useState(false);
  const [modelLists, setModelLists] = useState<{
    primary?: InferenceModelList;
    embedding?: InferenceModelList;
  }>({});
  const [listBusy, setListBusy] = useState<Target | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(settings.inference);
  }, [settings.inference]);

  const save = async (patch: Partial<NonNullable<OperatorSettings["inference"]>>) => {
    setBusy(true);
    setError(null);
    try {
      const next = await api.patchOperatorSettings({
        inference: { ...draft, ...patch },
      });
      onUpdated(next);
      setDraft(next.inference);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const refreshModels = useCallback(async (target: Target, probeUrl?: string) => {
    setListBusy(target);
    setError(null);
    try {
      const result = await api.listInferenceModels(target, probeUrl);
      setModelLists((prev) => ({ ...prev, [target]: result }));
      if (!result.ok && result.error) {
        setError(`${target}: ${result.error}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not list models");
    } finally {
      setListBusy(null);
    }
  }, []);

  const effective = settings.inferenceEffective;

  return (
    <SettingsBlock
      title="Inference endpoints"
      description="Point this operator install at local or remote llama.cpp servers. Empty fields fall back to ALTRASIA_* environment variables."
    >
      <div className="settings-fields">
        <label className="settings-field">
          <span className="settings-field-label">Primary LLM base URL</span>
          <input
            type="url"
            placeholder={envHint(settings, "primaryBaseUrl")}
            value={draft?.primaryBaseUrl ?? ""}
            disabled={busy}
            onChange={(e) => setDraft((d) => ({ ...d!, primaryBaseUrl: e.target.value }))}
            onBlur={() => save({ primaryBaseUrl: draft?.primaryBaseUrl ?? "" })}
          />
        </label>
        <div className="settings-model-row">
          <label className="settings-field settings-field-grow">
            <span className="settings-field-label">Primary model</span>
            <input
              type="text"
              list="settings-primary-models"
              placeholder={envHint(settings, "primaryModel")}
              value={draft?.primaryModel ?? ""}
              disabled={busy}
              onChange={(e) => setDraft((d) => ({ ...d!, primaryModel: e.target.value }))}
              onBlur={() => save({ primaryModel: draft?.primaryModel ?? "" })}
            />
            <datalist id="settings-primary-models">
              {modelLists.primary?.models.map((m) => (
                <option key={m.id} value={m.id} />
              ))}
            </datalist>
          </label>
          <button
            type="button"
            className="people-secondary"
            disabled={busy || listBusy === "primary"}
            onClick={() =>
              refreshModels("primary", draft?.primaryBaseUrl || undefined)
            }
          >
            {listBusy === "primary" ? "Listing…" : "List models"}
          </button>
        </div>
        {modelLists.primary?.ok && modelLists.primary.routerMode && (
          <p className="settings-block-foot">Router mode: multiple models available on this endpoint.</p>
        )}

        <label className="settings-field">
          <span className="settings-field-label">Embedding base URL</span>
          <input
            type="url"
            placeholder={envHint(settings, "embeddingBaseUrl")}
            value={draft?.embeddingBaseUrl ?? ""}
            disabled={busy}
            onChange={(e) => setDraft((d) => ({ ...d!, embeddingBaseUrl: e.target.value }))}
            onBlur={() => save({ embeddingBaseUrl: draft?.embeddingBaseUrl ?? "" })}
          />
        </label>
        <div className="settings-model-row">
          <label className="settings-field settings-field-grow">
            <span className="settings-field-label">Embedding model</span>
            <input
              type="text"
              list="settings-embedding-models"
              placeholder={envHint(settings, "embeddingModel")}
              value={draft?.embeddingModel ?? ""}
              disabled={busy}
              onChange={(e) => setDraft((d) => ({ ...d!, embeddingModel: e.target.value }))}
              onBlur={() => save({ embeddingModel: draft?.embeddingModel ?? "" })}
            />
            <datalist id="settings-embedding-models">
              {modelLists.embedding?.models.map((m) => (
                <option key={m.id} value={m.id} />
              ))}
            </datalist>
          </label>
          <button
            type="button"
            className="people-secondary"
            disabled={busy || listBusy === "embedding"}
            onClick={() =>
              refreshModels("embedding", draft?.embeddingBaseUrl || undefined)
            }
          >
            {listBusy === "embedding" ? "Listing…" : "List models"}
          </button>
        </div>
        {modelLists.embedding?.ok && modelLists.embedding.routerMode && (
          <p className="settings-block-foot">
            Router mode: pick the embedding model id exposed by your server.
          </p>
        )}

        {effective && (
          <p className="settings-block-foot">
            Active: primary {effective.mockLlm ? "(mock)" : effective.primaryModel ?? "—"} @{" "}
            {effective.primaryBaseUrl ?? "mock"} · embedding {effective.embeddingModel ?? "—"} @{" "}
            {effective.embeddingBaseUrl ?? "off"}
          </p>
        )}
        {settings.envDefaults?.mockLlm && !effective?.primaryBaseUrl && (
          <p className="settings-block-foot">
            Mock LLM is enabled until a primary base URL is configured (env or settings).
          </p>
        )}
      </div>
      {error && <p className="settings-error">{error}</p>}
    </SettingsBlock>
  );
}
