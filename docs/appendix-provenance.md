# Appendix — Provenance (SillyTavern)

> **Non-normative.** This appendix is for migration context only. Implementations MUST follow docs `00`–`22`, not SillyTavern behavior, unless explicitly adopted in normative text.

This appendix maps WorldEngine concepts to the SillyTavern fork from which they were extracted. **Implementers** may use it for migration; the main specification intentionally avoids ST-specific paths.

## MemPalace / mempalace (GitHub) — not in scope

**[MemPalace/mempalace](https://github.com/mempalace/mempalace)** (the Python open-source project: Wings/Rooms/Closets/Drawers, ChromaDB, coding-session mining, MCP tools) is **not** a WorldEngine dependency, design source, or implementation target.

WorldEngine **Memory** ([02-memory.md](02-memory.md)) is a separate subsystem: flat **locus keys**, **mind/world pools**, **witnessed diary**, and **mandatory recall** for narrative roleplay. Do not conflate it with MemPalace branding or hierarchy.

The SillyTavern extension also named `mempalace` (below) is **migration provenance only** — not the MemPalace GitHub product.

## Extension and module map

| WorldEngine doc | ST source (relative to SillyTavern root) |
|-----------------|------------------------------------------|
| 01-world-model | `public/scripts/extensions/chat-participant-roster/`, `group-chats.js`, `src/util/chat-roster-build.js` |
| 02-memory | `public/scripts/extensions/mempalace/index.js`, `recall-bundle.js`, `settings.html`, `manifest.json` (ST extension; not MemPalace GitHub) |
| 03-locations-and-presence | `location-presence.js`, `location-persist.js`, `location-drawer.js`, `location-create-popup.js`, `scene-framing.js`, `world-activity.js`, `narrative-presence.js`, `tools.js` |
| 04-communication | `communication-scopes.js`, `communication-compose.js`, `communication-mirror.js`, `COMMUNICATION_SCOPES.md`, `roster-hooks-register.js` |
| 05-tool-calling | `public/scripts/tool-calling.js`, `public/script.js` (invoke loop), `public/scripts/openai.js` |
| 06-web-tools | `public/scripts/extensions/web-tools/index.js`, `src/endpoints/search.js`, `src/endpoints/backends/chat-completions.js` (provider web search) |
| 07-approvals | `src/architect-filesystem/approvals.js`, `service.js`, `classify.js`, `src/endpoints/architect-filesystem.js`, web-tools approval polling |
| 08-real-world-capabilities | `docs/ARCHITECT_FILESYSTEM.md`, `docs/SCHEDULED_TASKS.md`, `character_agent_tools/`, `src/scheduler/` |
| 09-roles-and-privilege | `observer-omnibus.js`, `persona-guard.js`, `OPERATOR_ROSTER_API.md`, mempalace `diary_admin_avatars` |
| 10-prompt-injection | mempalace extension prompts, `recall-bundle.js`, `scene-framing.js`, `openai.js` perception hooks |
| 22-output-quality | OldPlans anti-loop policy; ST reasoning strip patterns (`reasoning.js`, model profiles) |

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

| Behavior | ST location | WorldEngine |
|----------|-------------|-------------|
| Mind loci in `extension_settings.mempalace.mindByAvatar` | `mempalace/index.js` | Mind pool per `characterId` |
| World loci in `chat_metadata.mempalace_world` | `mempalace/index.js` | World pool per `sceneId` |
| Fixture mirror keys `location:{id}:*` | `location-presence.js` `syncMempalaceLocationFixtures` | MP-2 |
| Mandatory recall blocking filter | `mempalace/recall-bundle.js` | MP-5, MP-9 (default **on** in v1; ST default off) |
| Witnessed diary + group fan-out | `mempalace/index.js` `tryAppendDiarySegment`, `getDiaryTargetAvatars` | MP-6, MP-17, MP-20 ([02-memory.md](02-memory.md) §1.3–1.4) |
| One approval apply on filesystem approve | `architect-filesystem/service.js` | [07-approvals.md](07-approvals.md) |
| Web plugin external to repo | `plugins/web-tools` on server | [06-web-tools.md](06-web-tools.md) |

## Intentional spec upgrades (ST → WorldEngine)

| Topic | SillyTavern behavior | WorldEngine norm |
|-------|----------------------|------------------|
| **Phone speakerphone** | Channel-global `mode: speakerphone` — all present at **both** linked locations hear the full call | Per-endpoint `speakerphone` on `endpoints[]` — bystanders at each scene hear one leg by default (C-8, C-9); toggle is independent per scene |
| **Narrator / meta** | Observer digest and omnibus patterns | `scope: narrator` + `channelKind=meta` excluded from cast perception |
| **Diary retention** | Append-only `diaryByAvatar`; window size = snippet width only | Same spirit: unbounded store, bounded mandatory-recall inject |
| **Persistence** | `extension_settings` + per-location jsonl | SQLite canonical store ([11-data-model.md](11-data-model.md)) |

## Configuration snapshot (reference deployment)

From ST `config.yaml` at extraction time:

- `scheduledTasks.enabled: true`
- `enableServerPlugins: true`
- `architectFilesystem.enabled: true`, `requireApprovalForWrites: true`, `unattendedWrites: false`

## Out of scope in ST not lifted

- SillyTavern preset/instruct templates
- Character card PNG V2 format
- Expressions, Stable Diffusion, vectors (noted as conflict in [02-memory.md](02-memory.md) §7)
- Core ST slash command framework (only domain-specific commands referenced)

## Document version

Extracted: 2026-05. Spec version: v1.0 (initial WorldEngine docs).
