# Appendix — Provenance (SillyTavern)

This appendix maps WorldEngine concepts to the SillyTavern fork from which they were extracted. **Implementers** may use it for migration; the main specification intentionally avoids ST-specific paths.

## Extension and module map

| WorldEngine doc | ST source (relative to SillyTavern root) |
|-----------------|------------------------------------------|
| 01-world-model | `public/scripts/extensions/chat-participant-roster/`, `group-chats.js`, `src/util/chat-roster-build.js` |
| 02-memory-palace | `public/scripts/extensions/mempalace/index.js`, `recall-bundle.js`, `settings.html`, `manifest.json` |
| 03-locations-and-presence | `location-presence.js`, `location-persist.js`, `location-drawer.js`, `location-create-popup.js`, `scene-framing.js`, `world-activity.js`, `narrative-presence.js`, `tools.js` |
| 04-communication | `communication-scopes.js`, `communication-compose.js`, `communication-mirror.js`, `COMMUNICATION_SCOPES.md`, `roster-hooks-register.js` |
| 05-tool-calling | `public/scripts/tool-calling.js`, `public/script.js` (invoke loop), `public/scripts/openai.js` |
| 06-web-tools | `public/scripts/extensions/web-tools/index.js`, `src/endpoints/search.js`, `src/endpoints/backends/chat-completions.js` (provider web search) |
| 07-approvals | `src/architect-filesystem/approvals.js`, `service.js`, `classify.js`, `src/endpoints/architect-filesystem.js`, web-tools approval polling |
| 08-real-world-capabilities | `docs/ARCHITECT_FILESYSTEM.md`, `docs/SCHEDULED_TASKS.md`, `character_agent_tools/`, `src/scheduler/` |
| 09-roles-and-privilege | `observer-omnibus.js`, `persona-guard.js`, `OPERATOR_ROSTER_API.md`, mempalace `diary_admin_avatars` |
| 10-prompt-injection | mempalace extension prompts, `recall-bundle.js`, `scene-framing.js`, `openai.js` perception hooks |

## Concept renaming (ST → WorldEngine)

| SillyTavern term | WorldEngine term |
|------------------|------------------|
| Group chat | World |
| Location / `group.chats[]` entry | Scene |
| `chat_id` / locationId | sceneId |
| Avatar filename (`Alice.png`) | characterId |
| `chat_metadata` | Scene header metadata |
| `extension_settings` | Operator/world settings store |
| `mempalace_*` tools | `memory_*` / `diary_*` tools (spec names) |
| `cpr_*` tools | `scene_*` / `comm_*` tools (spec names) |
| `webtools_invoke` | `webtools_invoke` (unchanged) |
| `architect_fs_*` | `fs_*` tools (spec names) |
| CPR / chat_participant_roster | Scene metadata block |

## Key ST-only behaviors preserved in spec

| Behavior | ST location |
|----------|-------------|
| Mind loci in `extension_settings.mempalace.mindByAvatar` | `mempalace/index.js` |
| World loci in `chat_metadata.mempalace_world` | `mempalace/index.js` |
| Fixture mirror keys `location:{id}:*` | `location-presence.js` `syncMempalaceLocationFixtures` |
| Mandatory recall blocking filter | `mempalace/recall-bundle.js` |
| One approval apply on filesystem approve | `architect-filesystem/service.js` |
| Web plugin external to repo | `plugins/web-tools` on server |

## Configuration snapshot (reference deployment)

From ST `config.yaml` at extraction time:

- `scheduledTasks.enabled: true`
- `enableServerPlugins: true`
- `architectFilesystem.enabled: true`, `requireApprovalForWrites: true`, `unattendedWrites: false`

## Out of scope in ST not lifted

- SillyTavern preset/instruct templates
- Character card PNG V2 format
- Expressions, Stable Diffusion, vectors (noted as conflict in 02 only)
- Core ST slash command framework (only domain-specific commands referenced)

## Document version

Extracted: 2026-05. Spec version: v1.0 (initial WorldEngine docs).
