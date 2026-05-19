export type SettingsCategoryId = "world" | "architect" | "cast" | "operations" | "server";

export type SettingsCategory = {
  id: SettingsCategoryId;
  label: string;
  description: string;
};

export const SETTINGS_CATEGORIES: SettingsCategory[] = [
  {
    id: "world",
    label: "World",
    description: "Policy, world status, package import/export, and scene briefings.",
  },
  {
    id: "architect",
    label: "Scenes & layout",
    description: "Geography, exits, and mini-map layout for this world.",
  },
  {
    id: "cast",
    label: "Cast",
    description:
      "Characters in this world, per-character web tool access, and AI-assisted creation.",
  },
  {
    id: "operations",
    label: "Operations",
    description: "Commissions and background work assigned to cast.",
  },
  {
    id: "server",
    label: "Server",
    description: "Global operator settings stored on this machine.",
  },
];

export function categoryPanelId(id: SettingsCategoryId): string {
  return `settings-panel-${id}`;
}
