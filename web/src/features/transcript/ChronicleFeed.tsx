import type { Message } from "../../api/client";
import { chronicleMessages, parseScope } from "../../lib/parse";
import { ChronicleEntry } from "./ChronicleEntry";

type Props = {
  messages: Message[];
  worldId: string;
};

function speakerLabel(m: Message): string {
  if (m.role === "user") return "You";
  const id = m.characterId ?? "";
  return id.replace(/^.*-char-/, "").replace(/^char-/, "") || "NPC";
}

export function ChronicleFeed({ messages, worldId }: Props) {
  const visible = chronicleMessages(messages);

  return (
    <div className="chronicle-feed" data-testid="chronicle-feed">
      {visible.length === 0 && (
        <p className="chronicle-feed__empty">The scene is quiet. Speak as persona to begin.</p>
      )}
      {visible.map((m) => {
        const sc = parseScope(m.metaJson);
        const perceived = m.perceivedByPersona !== false;
        return (
          <ChronicleEntry
            key={m.messageId}
            message={m}
            scope={sc}
            speakerLabel={speakerLabel(m)}
            perceived={perceived}
            worldId={worldId}
          />
        );
      })}
    </div>
  );
}
