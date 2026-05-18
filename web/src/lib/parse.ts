export function parseScope(metaJson: string): string {
  try {
    return JSON.parse(metaJson).communication?.scope ?? "public";
  } catch {
    return "public";
  }
}

export function parsePresent(raw: string): string[] {
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function structureLabel(structureId: string): string {
  return structureId.replace(/^struct-/, "").replace(/-/g, " ");
}

export function sceneStructureHints(layoutHintsJson?: string | null): {
  structureId?: string;
  fixtures?: string[];
} {
  if (!layoutHintsJson) return {};
  try {
    const hints = JSON.parse(layoutHintsJson);
    return {
      structureId: hints.structureId as string | undefined,
      fixtures: Array.isArray(hints.fixtures) ? hints.fixtures : undefined,
    };
  } catch {
    return {};
  }
}

export function structureTint(structureId?: string | null): string {
  if (!structureId) return "220";
  let hash = 0;
  for (let i = 0; i < structureId.length; i++) {
    hash = (hash * 31 + structureId.charCodeAt(i)) | 0;
  }
  return String(200 + (Math.abs(hash) % 40));
}
