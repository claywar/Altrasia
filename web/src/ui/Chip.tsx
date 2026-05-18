import type { ReactNode } from "react";

type Props = {
  label: string;
  initials?: string;
  hint?: string;
  children?: ReactNode;
};

export function Chip({ label, initials, hint, children }: Props) {
  const av = initials ?? label.slice(0, 2).toUpperCase();
  return (
    <span className="ui-chip" title={hint}>
      <span className="ui-chip__avatar" aria-hidden>
        {av}
      </span>
      <span>{label}</span>
      {children}
    </span>
  );
}
