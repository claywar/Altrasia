import { useEffect, useState } from "react";
import { api, type Approval } from "../api/client";

type Props = {
  worldId: string;
};

export function ApprovalsBanner({ worldId }: Props) {
  const [items, setItems] = useState<Approval[]>([]);

  const load = () =>
    api.listApprovals(worldId).then(setItems).catch(() => setItems([]));

  useEffect(() => {
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, [worldId]);

  if (items.length === 0) return null;

  return (
    <div className="approvals-banner">
      <span>
        {items.length} pending approval{items.length === 1 ? "" : "s"} (web/tools)
      </span>
      <ul>
        {items.map((a) => (
          <li key={a.approvalId}>
            <code>{a.toolName}</code>
            <button
              type="button"
              onClick={async () => {
                await api.approveApproval(worldId, a.approvalId);
                await load();
              }}
            >
              Approve
            </button>
            <button
              type="button"
              className="people-secondary"
              onClick={async () => {
                await api.denyApproval(worldId, a.approvalId);
                await load();
              }}
            >
              Deny
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
