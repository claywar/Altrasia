import { useState } from "react";
import { api, type GenerationJob } from "../api/client";

type Props = {
  worldId: string;
  jobId: string;
};

export function MessageRationale({ worldId, jobId }: Props) {
  const [open, setOpen] = useState(false);
  const [job, setJob] = useState<GenerationJob | null>(null);

  const load = async () => {
    if (job) {
      setOpen(!open);
      return;
    }
    const j = await api.getGeneration(worldId, jobId);
    setJob(j);
    setOpen(true);
  };

  return (
    <span className="msg-rationale">
      <button type="button" className="msg-info" onClick={load} title="Why this character spoke">
        ⓘ
      </button>
      {open && job && (
        <span className="msg-rationale-pop">
          {job.trigger}
          {job.continueDepth ? ` · depth ${job.continueDepth}` : ""} · {job.characterId.replace("char-", "")}
          {job.selectionRationaleJson && (
            <code>{job.selectionRationaleJson}</code>
          )}
        </span>
      )}
    </span>
  );
}
