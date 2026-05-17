# 19 — ComfyUI Media (Future)

**Status:** Post-v1. Same-machine ComfyUI integrated via [GpuResourceQueue](00-inference-runtime.md).

## 1. Goal

Scene illustrations, portraits, fixture icons—not a bolt-on gallery.

## 2. Requirements

| ID | Requirement |
|----|-------------|
| IMG-1 | ComfyUI HTTP at `comfy.baseUrl`; all renders enqueue as `kind: image`. |
| IMG-2 | Workflow templates: `scene_establishing`, `character_portrait`, `fixture_icon`, `map_thumbnail` in `data/workflows/`. |
| IMG-3 | Tool `image_generate` — prompt from output-only context; stripReasoning on caption locus. |
| IMG-4 | `mediaAsset`: assetId, path, sha256, workflowId, createdAt, sourceJobId. |
| IMG-5 | Optional `requireApprovalForImageGen`. |
| IMG-6 | Web UI regenerate via Observer; queue position visible. |
| IMG-7 | Cast MAY request only if policy allows; default Observer/operator only. |
| IMG-8 | Pause idle NPC before dropping operator image job. |
| IMG-9 | Workflow denylist; no diary capture of binary images. |

## 3. Memory

Store **caption + assetId** in world locus (`scene:{id}:image` or fixture key)—not pixels in loci.

## 4. v1

ComfyUI is **not implemented** in v1. GpuResourceQueue schema reserves `kind: image`.

## 5. Web UI (post-v1)

| UI spec | Maps to IMG |
|---------|-------------|
| UI-IMG-1 | v1 gray portrait placeholders in roster/messages |
| UI-IMG-2 | `ReferenceSheetPanel` — per-character reference images; IP-Adapter / `character_portrait` workflow for consistency |
| UI-IMG-3 | `SceneEstablishingShot` in scene header or left spatial panel |
| UI-IMG-4 | `ImageGenQueueBadge` on GPU strip (`kind: image`) |
| UI-IMG-5 | `RegenerateImageControl` in Observer Studio only (IMG-6, IMG-7) |

Wireframe WF-13: [guides/web-ui-wireframes.md](guides/web-ui-wireframes.md).

## Related documents

- [00-inference-runtime.md](00-inference-runtime.md)
- [18-location-maps.md](18-location-maps.md)
- [07-approvals.md](07-approvals.md)
