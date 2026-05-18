import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  className?: string;
};

export function Badge({ children, className = "" }: Props) {
  return <span className={`ui-badge ${className}`.trim()}>{children}</span>;
}
