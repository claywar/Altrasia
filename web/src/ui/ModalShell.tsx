import { useEffect, useRef, type MouseEvent, type ReactNode } from "react";
import { FocusTrap } from "./FocusTrap";

type Side = "right" | "left" | "center";

type Props = {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
  side?: Side;
  zIndex?: number;
  testId?: string;
  closeLabel?: string;
};

export function ModalShell({
  title,
  subtitle,
  onClose,
  children,
  side = "center",
  zIndex,
  testId,
  closeLabel = "Esc — Close",
}: Props) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const onOverlayClick = (e: MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  const scrimClass =
    side === "center"
      ? "ui-modal-scrim ui-modal-scrim--center"
      : side === "left"
        ? "ui-modal-scrim ui-modal-scrim--left"
        : "ui-modal-scrim";

  const panelClass =
    side === "center"
      ? "ui-modal-panel ui-modal-panel--full"
      : side === "left"
        ? "ui-modal-panel ui-modal-panel--left"
        : "ui-modal-panel ui-modal-panel--right";

  return (
    <div
      className={scrimClass}
      role="presentation"
      onClick={onOverlayClick}
      data-testid={testId}
      style={zIndex != null ? { zIndex } : undefined}
    >
      <FocusTrap>
        <div
          className={panelClass}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-shell-title"
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <header className="ui-modal-header">
            <div>
              <h2 id="modal-shell-title">{title}</h2>
              {subtitle ? (
                <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--muted)" }}>{subtitle}</p>
              ) : null}
            </div>
            <button ref={closeRef} type="button" className="ui-btn ui-btn--ghost ui-btn--sm" onClick={onClose}>
              {closeLabel}
            </button>
          </header>
          <div className="ui-modal-body">{children}</div>
        </div>
      </FocusTrap>
    </div>
  );
}
