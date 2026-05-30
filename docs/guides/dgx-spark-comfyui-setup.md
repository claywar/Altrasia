# DGX Spark — Native ComfyUI setup

**No Docker.** WorldEngine expects a native ComfyUI install on the same machine as Altrasia (typically port `8188`).

## Hardware

- DGX Spark: 128 GB unified memory max; plan for **~70 GB AI workload budget** (chat + image + embed).
- ARM64 + Blackwell (`sm_121`): use PyTorch **CUDA 13+ ARM64** wheels in a dedicated venv.

## Install (summary)

1. Clone ComfyUI: `git clone https://github.com/comfyanonymous/ComfyUI.git ~/ComfyUI`
2. Create venv: `python3.11 -m venv ~/ComfyUI/venv && source ~/ComfyUI/venv/bin/activate`
3. Install PyTorch per [NVIDIA Spark ComfyUI guide](https://build.nvidia.com/spark/comfy-ui) (cu130 ARM64 index).
4. `pip install -r requirements.txt`
5. Install models under `ComfyUI/models/` matching profile YAML in `config/models/image/`.
6. Launch with headroom for llama.cpp:

```bash
python main.py --listen 0.0.0.0 --port 8188 --reserve-vram 4096
```

Do **not** use `--gpu-only` or `--disable-mmap` on unified memory.

## Altrasia configuration

- Environment: `ALTRASIA_COMFY_URL=http://127.0.0.1:8188`
- Or **Settings → Media → ComfyUI base URL**
- Set memory budget (default 70 GB) and per-workflow profile defaults.

## Smoke test

```bash
python scripts/comfyui-smoke.py --workflow scene_establishing --profile z-image-turbo-default
```

## Memory policy

- `GpuResourceQueue` serializes chat and image jobs.
- After each image lease, Altrasia calls ComfyUI `POST /free` to unload models.
- Cancel during image jobs calls `POST /interrupt`.

## Custom profiles

Use **Settings → Media → Add profile** to register checkpoint filenames without editing repo YAML. Built-in profiles live in `config/models/image/`; operator profiles in `~/.altrasia/image-profiles/`.

## Optional wrapper

[SaladTechnologies/comfyui-api](https://github.com/SaladTechnologies/comfyui-api) can provide sync REST on port 3000 — point `comfyBaseUrl` there instead of `:8188` if desired. Workflow JSON and profile registry remain in Altrasia.
