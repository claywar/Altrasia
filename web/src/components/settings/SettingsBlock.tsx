import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  compact?: boolean;
  children: ReactNode;
};

export function SettingsBlock({ title, description, compact, children }: Props) {
  return (
    <section className={`settings-block ui-form-section${compact ? " settings-block-compact" : ""}`}>
      <h4 className="settings-block-title ui-form-section__title">{title}</h4>
      {description && <p className="settings-block-desc ui-form-section__desc">{description}</p>}
      {children}
    </section>
  );
}
