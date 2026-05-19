import { MarkdownBody } from "../../components/MarkdownBody";
import { MessageRationale } from "../../components/MessageRationale";
import type { Message } from "../../api/client";
import { isSocialIdleMessage, parseGenerationError } from "../../lib/parse";
import { ScopeBadge } from "../../ui/ScopeBadge";

type Props = {
  message: Message;
  scope: string;
  speakerLabel: string;
  perceived: boolean;
  worldId: string;
};

export function ChronicleEntry({ message, scope, speakerLabel, perceived, worldId }: Props) {
  const streaming = message.streamStatus === "streaming";
  const interrupted = message.streamStatus === "interrupted";
  const generationError = parseGenerationError(message.metaJson);
  const bodyText =
    message.outputText?.trim() ||
    (interrupted
      ? generationError ?? "Generation was interrupted before a reply was produced."
      : "");
  const isBanter = isSocialIdleMessage(message);
  const ariaLabel = `${speakerLabel}, ${scope}${isBanter ? ", sidebar banter" : ""}${perceived ? "" : ", not perceived"}`;

  return (
    <article
      className={[
        "chronicle-entry",
        `chronicle-entry--${scope}`,
        isBanter ? "chronicle-entry--banter" : "",
        streaming ? "chronicle-entry--streaming" : "",
        interrupted ? "chronicle-entry--interrupted" : "",
        perceived ? "" : "chronicle-entry--dimmed",
      ]
        .filter(Boolean)
        .join(" ")}
      aria-label={ariaLabel}
      title={perceived ? undefined : "Not perceived at your position"}
      data-testid="chronicle-entry"
    >
      <header className="chronicle-entry__header">
        <span className="chronicle-entry__speaker">{speakerLabel}</span>
        <ScopeBadge scope={scope} />
        {isBanter && <span className="chronicle-entry__banter-badge">Banter</span>}
        {message.role === "assistant" && message.generationJobId && (
          <MessageRationale worldId={worldId} jobId={message.generationJobId} />
        )}
        {streaming && <span className="chronicle-entry__generating">Generating…</span>}
      </header>
      <div className="chronicle-entry__body">
        {streaming ? (
          <p className="chronicle-entry__stream">
            {message.outputText}
            <span className="chronicle-entry__caret" aria-hidden />
          </p>
        ) : (
          <MarkdownBody>{bodyText}</MarkdownBody>
        )}
      </div>
    </article>
  );
}
