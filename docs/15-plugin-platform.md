# 15 — Plugin Platform (Future)

v1 ships **zero required plugins**. This document defines the target extension model for post-v1 modules (web-tools, maps, ComfyUI).

## 1. Goals

| Goal | Description |
|------|-------------|
| Extensibility | Third-party tools and hooks without forking core |
| Safety | Plugins cannot bypass approvals or MP-1 |
| Alignment | Maps and ComfyUI use same hooks (PL-6) |

## 2. Manifest

| ID | Requirement |
|----|-------------|
| PL-1 | Manifest fields: `id`, `version`, `hooks[]`, `tools[]`, `permissions[]`. |
| PL-2 | Hooks: `onGenerationStart`, `onToolInvoke`, `onMessageAppend`, `onApprovalRequired`. |
| PL-3 | Tools register via central registry ([05-tool-calling.md](05-tool-calling.md)); same gates as core tools. |
| PL-4 | No raw FS unless `architect` permission declared and approved. |
| PL-5 | v1 core toolset frozen; web-tools MAY ship as reference plugin in v2. |
| PL-6 | Map and ComfyUI integrations SHOULD use PL-1–PL-5. |

## 3. Discovery (implementation sketch)

| Source | Path |
|--------|------|
| Operator | `~/.worldengine/plugins/` |
| Project | `./plugins/` |
| Package | npm-style entry points (future) |

## 4. Hook contract

Hooks receive world-scoped context:

```typescript
// Illustrative — not normative code
interface PluginContext {
  worldId: string;
  characterId?: string;
  sceneId?: string;
}
```

Hooks MUST NOT mutate mind pools across characters (MP-1).

## 5. Permissions

| Permission | Grants |
|------------|--------|
| `tools.register` | Add function tools |
| `hooks.generation` | onGenerationStart |
| `filesystem` | Architect-class FS (approved) |
| `web` | Web search/fetch (approved) |

## 6. v1 status

Plugins are **not loaded** in v1. Core implements fixed tool registry only.

## Related documents

- [05-tool-calling.md](05-tool-calling.md)
- [07-approvals.md](07-approvals.md)
- [18-location-maps.md](18-location-maps.md)
- [19-comfyui-media.md](19-comfyui-media.md)
