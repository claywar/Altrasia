import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  children: ReactNode;
};

export function FormSection({ title, description, children }: Props) {
  return (
    <section className="ui-form-section">
      <h3 className="ui-form-section__title">{title}</h3>
      {description && <p className="ui-form-section__desc">{description}</p>}
      {children}
    </section>
  );
}
