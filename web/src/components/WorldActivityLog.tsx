import { useState } from "react";
import { MarkdownBody } from "./MarkdownBody";
import type { Message } from "../api/client";

type Props = {
  entries: Message[];
  charName: (characterId: string | null) => string;
};

function idleSourceLabel(source: string | null | undefined): string {
  if (source === "server_heartbeat") return "heartbeat";
  if (source === "tab_visible") return "tab";
  return "idle";
}

function formatTime(createdAt: string | undefined): string {
  if (!createdAt) return "";
  try {
    const d = new Date(createdAt);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function preview(text: string, max = 60): string {
  const t = text.replace(/\s+/g, " ").trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max)}…`;
}

export function WorldActivityLog({ entries, charName }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (entries.length === 0) return null;

  return (
    <div className="world-activity-log" data-testid="world-activity-log" aria-label="Ambient activity">
      <span className="world-activity-log__label">Activity</span>
      <ul className="world-activity-log__list">
        {entries.map((m) => {
          const open = expandedId === m.messageId;
          const streaming = m.streamStatus === "streaming";
          const name = charName(m.characterId);
          return (
            <li key={m.messageId} className="world-activity-log__item">
              <button
                type="button"
                className="world-activity-log__row"
                onClick={() => setExpandedId(open ? null : m.messageId)}
                aria-expanded={open}
              >
                <span className="world-activity-log__meta">
                  {formatTime(m.createdAt)}
                  {formatTime(m.createdAt) ? " · " : ""}
                  {name} · idle ({idleSourceLabel(m.idleSource)})
                  {streaming ? " · …" : ""}
                </span>
                {!open && !streaming && m.outputText && (
                  <span className="world-activity-log__preview">{preview(m.outputText)}</span>
                )}
                {streaming && (
                  <span className="world-activity-log__preview">Generating…</span>
                )}
              </button>
              {open && (
                <div className="world-activity-log__detail">
                  {streaming ? (
                    <p>{m.outputText}</p>
                  ) : (
                    <MarkdownBody>{m.outputText}</MarkdownBody>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
