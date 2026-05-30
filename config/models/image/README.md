# Image model profiles

Declarative profiles for ComfyUI image generation (`IMG-2`). Each profile selects a **model family** (workflow graph) and **checkpoint files** to inject.

## Memory budget (DGX Spark)

| Pool | Typical GB | Notes |
|------|------------|--------|
| OS + system reserve | 10–15 | Non-negotiable |
| Qwen 35B (llama.cpp) | 20–35 | Measure on your quant |
| Embedding model | 1–4 | Separate port |
| Image job peak | 6–24 | See `peakMemoryGb` per profile |
| Safety margin | 5–10 | Activation spikes |

**Planning ceiling:** ~70 GB for AI workloads (128 GB hardware max). Serialize chat and image via `GpuResourceQueue`; call ComfyUI `POST /free` after each image lease.

## Profile YAML schema

```yaml
profileId: sdxl-default          # required, unique slug
family: sdxl                     # sdxl | flux | z_image_turbo
displayName: "SDXL default"
peakMemoryGb: 8
builtin: true                    # optional; shipped profiles cannot be deleted
comfy:
  checkpoint: model.safetensors    # family-specific loader fields
defaults:
  steps: 20
  cfg: 7.0
  width: 1024
  height: 1024
capabilities:
  referenceImage: true
supportedWorkflows:
  - character_portrait
  - scene_establishing
  - fixture_icon
  - map_thumbnail
```

### Family-specific `comfy` keys

| family | keys |
|--------|------|
| `sdxl` | `checkpoint` |
| `flux` | `unet`, `clip_l`, `clip_t5`, `vae` |
| `z_image_turbo` | `diffusionModel`, `textEncoder`, `vae` |

## Locations

| Source | Path |
|--------|------|
| Built-in | `config/models/image/*.yaml` (repo) |
| Operator-created | `~/.altrasia/image-profiles/*.yaml` |

Resolution order for effective profile: request override → world policy → operator Settings → `sdxl-default`.
