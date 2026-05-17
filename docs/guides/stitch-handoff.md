# Stitch handoff — Pack A (v1 operator console)

**Non-normative.** High-fidelity mockups for Google Stitch (or similar) before implementation. Normative behavior: [14-web-ui.md](../14-web-ui.md). Wireframes: [web-ui-wireframes.md](web-ui-wireframes.md). Tokens: [design-tokens.yaml](design-tokens.yaml).

## Pack A screen list (v1 Sprint 2)

| Order | Wireframe | Screen |
|-------|-----------|--------|
| 1 | WF-9 | Empty / first run |
| 2 | WF-12 | World entry menu (loaded) |
| 3 | WF-1 | Default play shell |
| 4 | WF-2 | Left spatial panel (v1 rects only) |
| 5 | WF-3, WF-4 | Rail collapsed; tablet drawer |
| 6 | WF-5, WF-18, WF-19 | Message finalized, streaming, interrupted |
| 7 | WF-6 | Persona compose |
| 8 | WF-20, WF-21 | Queue strip; rationale popover |
| 9 | WF-8 | Knock signal |
| 10 | WF-7 | Observer Studio |
| 11 | WF-10, WF-11 | Settings; approvals |
| 12 | WF-17 | Memory inspector |

## Global Stitch prompt block

Paste at the start of each session:

```
Altrasia operator console — dark, low-glare, desktop-first (1280px+).
NOT a generic chat app: no pill bubbles, gradient avatars, or light theme.
Layout: center transcript hero; RIGHT rail = Places, People, Signals (260px);
optional LEFT spatial panel (collapsed default). TopBar + GpuQueueStrip always visible.
Colors and scope badges: use design-tokens.yaml (HSL). Scope labels required on badges.
Transcript: 15–16px; markdown only after streamStatus=final; streaming = plain text + caret.
Motion: 150–200ms overlays only; respect prefers-reduced-motion.
```

## Explicit exclusions (do not mock in Pack A)

| Item | Why |
|------|-----|
| WF-2b | v1.1 building envelopes + mapShape |
| WF-13 | ComfyUI portraits |
| WF-14–WF-16 | Phase 6 world map, level stack, MapDraft |
| Phone UI, global heartbeat | v1.1 |
| Character authoring wizard | Phase 3 |
| Light theme | v1 non-goal |

## Reference images

| PNG | Pack | Use with |
|-----|------|----------|
| altrasia-structured-minimap.png | v1 | WF-2 |
| altrasia-building-envelope-minimap.png | v1.1 | WF-2b |
| altrasia-architecture-diagram-minimap.png | v1.1 | WF-2b |
| altrasia-world-map-overlay-example.png | Phase 6 | WF-14 |
| altrasia-level-stack-example.png | Phase 6 | WF-15 |

See [reference-images/README.md](reference-images/README.md).

## Suggested Stitch order

1. Shell + tokens (WF-1, WF-20 idle/busy)
2. Transcript states (WF-5, WF-18, WF-19, WF-21)
3. Compose + right rail (WF-6, WF-1 rail sections)
4. Spatial panel v1 rects (WF-2)
5. Overlays (WF-7, WF-10, WF-11, WF-17)
6. Edge states (WF-8, WF-9, WF-12, WF-4)

## API fields for realistic copy

Rationale popover and queue strip use [12-api-sketch.md](../12-api-sketch.md) §7: `selectionRationaleJson`, `trigger`, `continueDepth`, `GET .../generations/{jobId}`. Messages expose `generationJobId` on assistant rows.

## Pack B (later)

WF-2b, envelope reference PNGs, §21.2–§21.3 in [14-web-ui.md](../14-web-ui.md).
