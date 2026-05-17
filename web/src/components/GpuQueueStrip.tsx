export type QueueJob = {
  jobId: string;
  characterId: string;
  trigger: string;
  continueDepth?: number;
  selectionRationaleJson?: string;
  status?: string;
};

type Props = {
  busy: boolean;
  depth: number;
  estimatedWaitMs?: number;
  currentJob?: QueueJob | null;
  onCancel?: () => void;
};

function parseRationale(raw: string | undefined): string | null {
  if (!raw) return null;
  try {
    const o = JSON.parse(raw) as { pick?: string; characterId?: string; factors?: string };
    if (o.factors) return o.factors;
    if (o.pick && o.characterId) return `${o.pick} → ${o.characterId.replace("char-", "")}`;
    return raw;
  } catch {
    return raw;
  }
}

export function GpuQueueStrip({
  busy,
  depth,
  estimatedWaitMs,
  currentJob,
  onCancel,
}: Props) {
  const rationale = parseRationale(currentJob?.selectionRationaleJson);
  const waitSec =
    estimatedWaitMs && estimatedWaitMs > 0
      ? `~${Math.ceil(estimatedWaitMs / 1000)}s`
      : null;

  return (
    <div className={`queue-strip-panel ${busy ? "busy" : ""}`} title="GPU queue (UI-2)">
      <span className="queue-status">{busy ? "GPU busy" : "GPU idle"}</span>
      {busy && depth > 0 && (
        <span className="queue-meta">
          depth {depth}
          {waitSec ? ` · est. ${waitSec}` : ""}
        </span>
      )}
      {currentJob && (
        <span className="queue-job">
          {currentJob.trigger}
          {currentJob.continueDepth ? ` · continue ${currentJob.continueDepth}` : ""}
          {" · "}
          {currentJob.characterId.replace("char-", "")}
        </span>
      )}
      {rationale && <span className="queue-rationale">{rationale}</span>}
      {busy && currentJob && onCancel && (
        <button type="button" className="queue-cancel" onClick={onCancel}>
          Cancel
        </button>
      )}
    </div>
  );
}
