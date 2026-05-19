import type { CharacterDefinition, WebToolsAccess, WorldPolicy } from "../api/client";

export const WEB_ACCESS_OPTIONS: {
  value: WebToolsAccess;
  label: string;
  hint: string;
}[] = [
  { value: "off", label: "Off", hint: "No web tools" },
  {
    value: "ask",
    label: "Ask each time",
    hint: "Requires your approval before each fetch",
  },
  {
    value: "allow",
    label: "Allowed",
    hint: "Pre-authorized; skips approval prompts",
  },
];

export function roleDefaultWebAccess(
  sceneRole: string | undefined,
  policy: WorldPolicy | undefined
): WebToolsAccess | undefined {
  if (!sceneRole || !policy?.defaultWebToolsAccessBySceneRole) return undefined;
  const raw = policy.defaultWebToolsAccessBySceneRole[sceneRole];
  if (raw === "off" || raw === "ask" || raw === "allow") return raw;
  return undefined;
}

export function effectiveWebToolsAccess(
  definition: CharacterDefinition | undefined,
  sceneRole: string | undefined,
  policy: WorldPolicy | undefined
): { access: WebToolsAccess; fromRoleDefault: boolean } {
  const explicit = definition?.webToolsAccess;
  if (explicit === "off" || explicit === "ask" || explicit === "allow") {
    return { access: explicit, fromRoleDefault: false };
  }
  const roleDefault = roleDefaultWebAccess(sceneRole, policy);
  if (roleDefault) {
    return { access: roleDefault, fromRoleDefault: true };
  }
  return { access: "off", fromRoleDefault: false };
}

export function webAccessOptionLabel(
  value: WebToolsAccess,
  fromRoleDefault: boolean
): string {
  const opt = WEB_ACCESS_OPTIONS.find((o) => o.value === value);
  const base = opt?.label ?? value;
  if (fromRoleDefault && value !== "off") {
    return `${base} (role default)`;
  }
  return base;
}
