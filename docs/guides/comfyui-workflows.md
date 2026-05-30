# ComfyUI workflows (operator summary)

Workflow API JSON lives under `data/workflows/{workflowId}/{family}.api.json`.

## Use cases

| workflowId | Purpose |
|------------|---------|
| `character_portrait` | Cast avatars; IP-Adapter when profile supports `referenceImage` |
| `scene_establishing` | Wide scene header / spatial panel |
| `fixture_icon` | Small fixture icons |
| `map_thumbnail` | Map / place thumbnails |

## Families shipped

| family | Variants | Notes |
|--------|----------|-------|
| `sdxl` | all four | Reference portraits |
| `z_image_turbo` | all four | Fast, ~12 GB peak |
| `flux` | portrait, scene | Quality option, NF4 profile |

## Re-export procedure

1. Prototype in ComfyUI canvas using the family template.
2. Memory-profile with chat model loaded; update `peakMemoryGb` in profile YAML.
3. Export **API format** to `data/workflows/{id}/{family}.api.json`.
4. Ensure `_altrasia.inject` node IDs match prompt/seed/checkpoint injection points.
5. Run `python scripts/comfyui-smoke.py --workflow … --profile …`.

## Operator profiles

Add checkpoints via **Settings → Media** (not by editing repo files). See [config/models/image/README.md](../../config/models/image/README.md).

Install details: [dgx-spark-comfyui-setup.md](dgx-spark-comfyui-setup.md).
