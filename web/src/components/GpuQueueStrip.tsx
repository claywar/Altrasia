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
  leaseKind?: string | null;
  onCancel?: () => void;
};

function parseRationale(raw: string | undefined): string | null {
  if (!raw) return null;
  try {
    const o = JSON.parse(raw) as {
      pick?: string;
      characterId?: string;
      factors?: string;
      idle_source?: string;
    };
    if (o.idle_source === "server_heartbeat") return "idle · server heartbeat";
    if (o.idle_source === "tab_visible") return "idle · tab visible";
    if (o.factors) return o.factors;
    if (o.pick && o.characterId) return `${o.pick} → ${o.characterId.replace("char-", "")}`;
    return raw;
  } catch {
    return raw;
  }
}

function leaseLabel(kind: string | null | undefined): string | null {
  if (!kind) return null;
  if (kind === "character_draft") return "character draft";
  if (kind === "generation") return null;
  return kind.replace(/_/g, " ");
}

export function GpuQueueStrip({
  busy,
  depth,
  estimatedWaitMs,
  currentJob,
  leaseKind,
  onCancel,
}: Props) {
  const rationale = parseRationale(currentJob?.selectionRationaleJson);
  const lease = leaseLabel(leaseKind);
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
      {leaseKind === "image" && <span className="queue-image-badge">Image</span>}
      {lease && !currentJob && <span className="queue-rationale">{lease}</span>}
      {rationale && <span className="queue-rationale">{rationale}</span>}
      {busy && currentJob && onCancel && (
        <button type="button" className="queue-cancel" onClick={onCancel}>
          Cancel
        </button>
      )}
    </div>
  );
}
