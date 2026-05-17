# Appendix — Glossary

| Term | Definition |
|------|------------|
| **Architect** | Builder-role character with filesystem, scheduler, and character admin tools |
| **Approval** | Operator gate before side-effecting tools apply |
| **Briefing fixture** | Scene fixture that mirrors shared text into world pool (`briefing:{sceneId}:…`) |
| **Cast** | All characters who are members of a world |
| **Commission** | Diegetic errand assigned to a cast member; research defaults to assignee mind pool (COM-1) |
| **Commons (world)** | World-scoped institutional loci; recall gated by allowlist (MP-22) |
| **Diary** | Witnessed episodic memory: rolling perceivable scene snippets, stored per character |
| **Diary fan-out** | On capture, the same segment appended to every present cast member's diary (MP-20) |
| **Witnessed diary** | Episodic memory of dialogue a character could perceive in play—not speaker-only monologue |
| **Diary admin** | Character allowed to read other characters' diaries via tool |
| **Discrete fixture** | Scene object that can be picked up or moved as a unit |
| **Aggregate fixture** | Harvestable scene object with limited picks / depletion |
| **Fixture** | Persistent object belonging to a scene, not a character's inventory |
| **Inventory** | Items worn, held, or contained by a character (world-scoped) |
| **Locus** | Named key in memory holding string facts |
| **Mandatory recall** | Authoritative pre-generation memory block (diary + loci) |
| **Mind pool** | Private memory loci per character |
| **Observer** | Control-surface character: digest, Studio meta-chat, narrator/deus ex modes |
| **Observer Studio** | Web UI slide-over for meta channel tuning ([14-web-ui.md](14-web-ui.md)) |
| **GpuResourceQueue** | Single-GPU scheduler for chat, embed, and future image jobs |
| **channelKind** | `scene` (in-fiction transcript) or `meta` (Observer Studio only) |
| **CrossSceneSignal** | Durable knock/ring/buzz between scenes; v1 tracks state; response emergent (CC-11a) |
| **Character draft** | In-progress LLM-proposed `definitionJson` before operator approve ([24-character-authoring.md](24-character-authoring.md)) |
| **doorState** | Exit field: `closed`, `unlocked`, `open`, `broken` ([03-locations-and-presence.md](03-locations-and-presence.md) §3.3) |
| **World heartbeat** | Global server setting for `idle_timer` when UI disconnected ([08-real-world-capabilities.md](08-real-world-capabilities.md) §8) |
| **Debate activity** | `scene.activity` overlay with phased turns and mind-pool synthesis (DEB-1) |
| **EvidenceRecord** | Provenance metadata linked to a locus (MP-21) |
| **focusTags** | Optional character definition tags for commission filtering |
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
| **World activity** | Background NPC generations (idle/reactive/continue) |
| **agent_continue** | Trigger: follow-up NPC job after a cast scene line (AO-19) |
| **scoreSpeakers** | Orchestrator function: weighted pick among eligible cast (AO-18) |
| **Speak-readiness probe** | Bounded FTS query per character for scheduling relevance (AO-17) |
| **speechWeight** | Character trait 0–1 biasing how often they are selected to speak |
| **World pool** | Shared memory loci for a scene's objective facts |
| **WorldEngine** | This specification's target platform name |
| **Model profile** | Config bundle per LLM (e.g. `qwen3.6-35b-a3b`) — router id, stripReasoning tags |
