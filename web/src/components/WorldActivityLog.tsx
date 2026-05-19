import { useEffect, useRef, useState } from "react";
import { MarkdownBody } from "./MarkdownBody";
import { Button } from "../ui/Button";
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

function ActivityIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M2 12h2.5M2 8h5M2 4h8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <circle cx="13" cy="12" r="1.25" fill="currentColor" />
      <circle cx="11" cy="8" r="1.25" fill="currentColor" />
      <circle cx="13" cy="4" r="1.25" fill="currentColor" />
    </svg>
  );
}

export function WorldActivityLog({ entries, charName }: Props) {
  const [panelOpen, setPanelOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!panelOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setPanelOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPanelOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [panelOpen]);

  if (entries.length === 0) return null;

  const streaming = entries.some((m) => m.streamStatus === "streaming");

  return (
    <div ref={rootRef} className="world-activity-log" data-testid="world-activity-log">
      <Button
        variant="ghost"
        size="icon"
        className={`world-activity-log__trigger${streaming ? " world-activity-log__trigger--live" : ""}`}
        onClick={() => setPanelOpen((open) => !open)}
        aria-expanded={panelOpen}
        aria-haspopup="dialog"
        title="Ambient activity"
        aria-label={`Ambient activity, ${entries.length} entries`}
      >
        <ActivityIcon />
        {streaming && <span className="world-activity-log__live-dot" aria-hidden />}
      </Button>
      {panelOpen && (
        <div
          className="world-activity-log__panel"
          role="dialog"
          aria-label="Ambient activity log"
          data-testid="world-activity-log-panel"
        >
          <div className="world-activity-log__panel-header">
            <span className="world-activity-log__label">Activity</span>
            <span className="world-activity-log__count">{entries.length}</span>
          </div>
          <ul className="world-activity-log__list">
            {entries.map((m) => {
              const open = expandedId === m.messageId;
              const rowStreaming = m.streamStatus === "streaming";
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
                      {rowStreaming ? " · …" : ""}
                    </span>
                    {!open && !rowStreaming && m.outputText && (
                      <span className="world-activity-log__preview">{preview(m.outputText)}</span>
                    )}
                    {rowStreaming && (
                      <span className="world-activity-log__preview">Generating…</span>
                    )}
                  </button>
                  {open && (
                    <div className="world-activity-log__detail">
                      {rowStreaming ? (
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
      )}
    </div>
  );
}
