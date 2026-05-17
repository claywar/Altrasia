# Appendix — Glossary

| Term | Definition |
|------|------------|
| **Architect** | Builder-role character with filesystem, scheduler, and character admin tools |
| **Approval** | Operator gate before side-effecting tools apply |
| **Cast** | All characters who are members of a world |
| **Diary** | Episodic memory segments auto-captured from a character's assistant messages |
| **Diary admin** | Character allowed to read other characters' diaries via tool |
| **Discrete fixture** | Scene object that can be picked up or moved as a unit |
| **Aggregate fixture** | Harvestable scene object with limited picks / depletion |
| **Fixture** | Persistent object belonging to a scene, not a character's inventory |
| **Inventory** | Items worn, held, or contained by a character (world-scoped) |
| **Locus** | Named key in the memory palace holding string facts |
| **Mandatory recall** | Authoritative pre-generation memory block (diary + loci) |
| **Mind pool** | Private memory loci per character |
| **Observer** | Control-surface character: digest, Studio meta-chat, narrator/deus ex modes |
| **Observer Studio** | Web UI slide-over for meta channel tuning ([14-web-ui.md](14-web-ui.md)) |
| **GpuResourceQueue** | Single-GPU scheduler for chat, embed, and future image jobs |
| **channelKind** | `scene` (in-fiction transcript) or `meta` (Observer Studio only) |
| **CrossSceneSignal** | Durable knock/ring/buzz between scenes (v1 track) |
| **outputText** | Post–stripReasoning message text used for durable memory |
| **Narrator scope** | Observer scene lines perceivable by all present at scene |
| **Phone endpoint** | One scene side of a call; has its own `speakerphone` flag |
| **Handset (phone)** | Default: bystanders overhear one leg (local scene speech only) |
| **Speakerphone (phone)** | Per-endpoint toggle: full call audible to present cast at that scene only |
| **Persona** | Human operator representation in presence and roster |
| **Present** | Characters (or persona) currently at a scene |
| **Recall protocol** | Instructional prompt listing pools, indexes, and tool budgets |
| **Scene** | Location within a world with its own transcript and presence |
| **Scene framing** | Per-character prompt slice describing current scene and present cast |
| **Stealth tool** | Tool that does not write transcript rows or recurse |
| **Transcript** | Ordered message log for one scene |
| **World** | Container for scenes, cast, and world-scoped inventory/channels |
| **World activity** | Background NPC generations (idle/reactive) |
| **World pool** | Shared memory loci for a scene's objective facts |
| **WorldEngine** | This specification's target platform name |
| **Model profile** | Config bundle per LLM (e.g. `qwen3.6-35b-a3b`) — router id, stripReasoning tags |
