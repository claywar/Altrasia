import { useEffect, useState } from "react";
import { api, type Approval } from "../api/client";

type Props = {
  worldId: string;
};

function approvalLabel(a: Approval, castNames: Record<string, string>): string {
  const who = a.characterId ? castNames[a.characterId] ?? a.characterId : "unknown";
  const q = (a.params?.query ?? a.params?.url ?? "") as string;
  const detail = q ? `: ${String(q).slice(0, 80)}` : "";
  return `${who} — ${a.toolName}${detail}`;
}

export function ApprovalsBanner({ worldId }: Props) {
  const [items, setItems] = useState<Approval[]>([]);
  const [castNames, setCastNames] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState<string | null>(null);

  const load = () =>
    Promise.all([
      api.listApprovals(worldId),
      api.listCharacters(worldId),
    ])
      .then(([approvals, cast]) => {
        setItems(approvals);
        const names: Record<string, string> = {};
        for (const c of cast) {
          names[c.characterId] = c.displayName;
        }
        setCastNames(names);
      })
      .catch(() => setItems([]));

  useEffect(() => {
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, [worldId]);

  if (items.length === 0 && !notice) return null;

  return (
    <div className="approvals-banner">
      <span>
        {items.length} pending approval{items.length === 1 ? "" : "s"} (web/tools)
      </span>
      {notice && <p className="settings-muted">{notice}</p>}
      <ul>
        {items.map((a) => (
          <li key={a.approvalId}>
            <code>{approvalLabel(a, castNames)}</code>
            <button
              type="button"
              onClick={async () => {
                const out = await api.approveApproval(worldId, a.approvalId);
                if (out.followUpJobId) {
                  setNotice("Approved — character may reply with the fetched result.");
                } else {
                  setNotice("Approved.");
                }
                await load();
                setTimeout(() => setNotice(null), 6000);
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
