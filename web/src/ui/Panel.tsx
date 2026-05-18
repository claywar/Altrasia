import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  className?: string;
};

export function Panel({ children, className = "" }: Props) {
  return <div className={`ui-panel ${className}`.trim()}>{children}</div>;
}
