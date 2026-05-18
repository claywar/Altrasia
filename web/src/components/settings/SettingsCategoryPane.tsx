import type { ReactNode } from "react";
import {
  SETTINGS_CATEGORIES,
  categoryPanelId,
  type SettingsCategoryId,
} from "./settingsNav";

type Props = {
  categoryId: SettingsCategoryId;
  children: ReactNode;
};

export function SettingsCategoryPane({ categoryId, children }: Props) {
  const meta = SETTINGS_CATEGORIES.find((c) => c.id === categoryId)!;
  return (
    <div
      id={categoryPanelId(categoryId)}
      role="tabpanel"
      aria-labelledby={`settings-tab-${categoryId}`}
      className="settings-content"
    >
      <div className="settings-category-intro">
        <h3>{meta.label}</h3>
        <p className="settings-muted">{meta.description}</p>
      </div>
      <div className="settings-content-body">{children}</div>
    </div>
  );
}
