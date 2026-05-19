import { useEffect, useState } from "react";
import { api, type GenerationJob } from "../api/client";
import { parseToolCallsFromRationale } from "../lib/parse";

type Props = {
  worldId: string;
  jobId: string;
};

export function MessageRationale({ worldId, jobId }: Props) {
  const [open, setOpen] = useState(false);
  const [job, setJob] = useState<GenerationJob | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setJob(null);
    setOpen(false);
    setLoading(false);
  }, [jobId]);

  const load = async () => {
    if (open && job) {
      setOpen(false);
      return;
    }
    if (job) {
      setOpen(true);
      return;
    }
    setLoading(true);
    try {
      const j = await api.getGeneration(worldId, jobId);
      setJob(j);
      setOpen(true);
    } finally {
      setLoading(false);
    }
  };

  const toolCalls = job ? parseToolCallsFromRationale(job.selectionRationaleJson) : [];
  const selectionJson =
    job?.selectionRationaleJson && toolCalls.length > 0
      ? (() => {
          try {
            const parsed = JSON.parse(job.selectionRationaleJson) as Record<string, unknown>;
            const { toolCalls: _tc, ...rest } = parsed;
            return Object.keys(rest).length > 0 ? JSON.stringify(rest, null, 2) : null;
          } catch {
            return job.selectionRationaleJson;
          }
        })()
      : job?.selectionRationaleJson ?? null;

  return (
    <span className="msg-rationale">
      <button
        type="button"
        className="msg-info"
        onClick={load}
        disabled={loading}
        title="Generation details (trigger, rationale, tool calls)"
        aria-expanded={open}
      >
        {loading ? "…" : "ⓘ"}
      </button>
      {open && job && (
        <span className="msg-rationale-pop">
          <span>
            {job.trigger}
            {job.continueDepth ? ` · depth ${job.continueDepth}` : ""} ·{" "}
            {job.characterId.replace("char-", "")}
          </span>
          {selectionJson && <code>{selectionJson}</code>}
          {toolCalls.length > 0 && (
            <span className="msg-rationale-tools" data-testid="msg-tool-calls">
              <strong>Tool calls ({toolCalls.length})</strong>
              {toolCalls.map((tc, i) => (
                <code key={`${tc.name}-${i}`}>
                  {tc.name}({JSON.stringify(tc.arguments)})
                  {"\n→ "}
                  {tc.result}
                </code>
              ))}
            </span>
          )}
        </span>
      )}
    </span>
  );
}
