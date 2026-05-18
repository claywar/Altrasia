import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  className?: string;
};

export function Card({ children, className = "" }: Props) {
  return <div className={`ui-card ${className}`.trim()}>{children}</div>;
}
