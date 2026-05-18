import { useEffect, useRef, type MouseEvent, type ReactNode } from "react";
import {
  SETTINGS_CATEGORIES,
  categoryPanelId,
  type SettingsCategoryId,
} from "./settingsNav";

type Props = {
  worldName: string;
  activeCategory: SettingsCategoryId;
  onCategoryChange: (id: SettingsCategoryId) => void;
  onClose: () => void;
  children: ReactNode;
};

const FOCUSABLE =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function SettingsShell({
  worldName,
  activeCategory,
  onCategoryChange,
  onClose,
  children,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
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

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    panel.addEventListener("keydown", onKeyDown);
    return () => panel.removeEventListener("keydown", onKeyDown);
  }, [activeCategory]);

  const onOverlayClick = (e: MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      className="settings-overlay"
      role="presentation"
      onClick={onOverlayClick}
    >
      <div
        ref={panelRef}
        className="settings-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-dialog-title"
        onClick={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className="settings-header">
          <div className="settings-header-titles">
            <h2 id="settings-dialog-title">Settings</h2>
            <p className="settings-world-name">{worldName}</p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose}>
            Esc — Close
          </button>
        </header>
        <div className="settings-body">
          <nav className="settings-nav" role="tablist" aria-label="Settings categories">
            {SETTINGS_CATEGORIES.map((cat) => {
              const selected = activeCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  type="button"
                  role="tab"
                  id={`settings-tab-${cat.id}`}
                  className={`settings-nav-item${selected ? " selected" : ""}`}
                  aria-selected={selected}
                  aria-controls={categoryPanelId(cat.id)}
                  onClick={() => onCategoryChange(cat.id)}
                >
                  {cat.label}
                </button>
              );
            })}
          </nav>
          {children}
        </div>
      </div>
    </div>
  );
}

