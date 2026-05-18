import type { ReactNode } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
  side?: "left" | "right";
  children: ReactNode;
  testId?: string;
};

export function Drawer({ open, onClose, side = "left", children, testId }: Props) {
  if (!open) return null;
  return (
    <>
      <div className="ui-drawer-backdrop" onClick={onClose} aria-hidden />
      <aside
        className={`ui-drawer${side === "right" ? " ui-drawer--right" : ""}`}
        data-testid={testId}
      >
        {children}
      </aside>
    </>
  );
}
