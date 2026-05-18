import type { ReactNode } from "react";

type Props = {
  title: string;
  children: ReactNode;
  className?: string;
  testId?: string;
};

export function RailSection({ title, children, className = "", testId }: Props) {
  return (
    <section className={`ui-rail-section ${className}`.trim()} data-testid={testId}>
      <h3 className="ui-rail-section__title">{title}</h3>
      {children}
    </section>
  );
}
