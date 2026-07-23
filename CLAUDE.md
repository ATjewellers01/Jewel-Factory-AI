# CLAUDE.md — AI-Features service

Guidance for Claude Code / any agent working in this repo.

## What this is

**ONE Python service for ALL Jewel Factory AI.** Deploy once (a Hugging Face
Docker Space, like the old `embedder`); every AI feature is one endpoint. The
Jewel Factory Next.js app calls this at `AI_FEATURES_URL` (and `EMBEDDER_URL` —
the OpenCLIP embedder is merged in here, see below). Repo:
`github.com/teamai-botivate/Jewel-Factory_AI`.

**Core idea:** never spin up a separate service per AI feature. A new feature =
a new `routes/<x>.py` + one `include_router` line in `main.py` + redeploy. Same
URL, same auth.

## Stack
Python 3.10 · FastAPI · uvicorn · Pillow · OpenAI SDK (gpt-image-2 + gpt-4o) ·
open-clip-torch + CPU torch (for `/embed/*`). Docker Space, port **7860**.

## Layout
```
main.py            FastAPI app; mounts all routers; /health; x-api-key guard
lib/
  config.py        OpenAI client (lazy) + env (API keys, model names)
  prompts.py       CATALOG_PROMPT, AR position prompts, describe prompt, extraInstructions helper
  image_utils.py   normalize_to_png, verify_and_center (crop+pad transparent PNG)
routes/
  catalog.py       POST /catalog       raw image (+extraInstructions) -> studio catalog image (base64)
  transparent.py   POST /transparent   raw image + jewelleryType (+extra) -> transparent try-on PNG (base64)
  describe.py      POST /describe       image + specs (+extra) -> { designName, description } (gpt-4o vision)
  embed.py         POST /embed/image|/embed/text|/embed/hybrid|/embed/image/batch -> OpenCLIP 512-d (visual search)
Dockerfile · requirements.txt · README.md (HF YAML) · INTEGRATION.md · .env.example
```

## Endpoints & contracts

| Path | Input (multipart unless noted) | Output |
|---|---|---|
| `POST /catalog` | `image`, `extraInstructions?` | `{ imageBase64, mimeType }` |
| `POST /transparent` | `image`, `jewelleryType`, `extraInstructions?` | `{ imageBase64, mimeType }` |
| `POST /describe` | `image`, `category`, `subCategory`, `weight`, `purity`, `extraInstructions?` | `{ designName, description }` |
| `POST /embed/image` | `file` | `{ dim, embedding }` |
| `POST /embed/text` | JSON `{ text }` | `{ dim, embedding }` |
| `POST /embed/hybrid` | `text?`, `weight`, `file?` | `{ dim, embedding }` |
| `POST /embed/image/batch` | `files[]` | `{ dim, embeddings[] }` |
| `GET /health` | — | `{ ok, service, openai }` |

`jewelleryType`: necklace · earring_left · earring_right · ring_index · ring_middle · bangle.
`extraInstructions` = the manufacturer's **regenerate** note (appended to the base prompt). Empty = default.

## Transparent try-on: 2-step pipeline (`routes/transparent.py`, `lib/prompts.py`)
Matches the proven Colab notebook — **two OpenAI calls per `/transparent` request**, not one:
1. **Step 1** (`TRANSPARENT_MODEL`, default `gpt-image-2`) — `build_ar_position_prompt()` positions the product on a plain solid light-grey (`#e0e0e0`) background. NOT transparent yet.
2. **Step 2** (`TRANSPARENT_BG_MODEL`, default `gpt-image-1`) — `build_ar_transparency_prompt()` + the native `background="transparent"` API param strips step 1's grey background to real alpha transparency.

Why 2 steps + 2 models: a single-call version that only *asks* for transparency in
the prompt text sometimes shipped an **opaque black background** instead (gpt-image
occasionally fails to remove backgrounds cleanly, especially on complex/reflective
jewelry) — `img.getbbox()` in `verify_and_center` doesn't catch this since an opaque
black pixel is still "non-zero." The native `background="transparent"` parameter
(only reliable on gpt-image-1) is a real API guarantee, not just a prompt request.
`image_utils.verify_and_center` also now checks the four corners are actually
transparent before cropping, and raises (→ 502, retry-able) if they aren't.

The transparent PNG is for **2D virtual try-on**, so it must contain only the FRONT-facing worn part, positioned as worn (step 1's job):
- **necklace**: front pendant/bib + two open front strands curving toward the shoulders — an open **U/V**, NOT a closed loop. Omit the rear neck chain + clasp.
- **bangle**: front arc of the band only; omit the part that wraps behind the wrist.
- **earrings/rings**: already front-only, single/pair/top-down.
Old assets generated before this convention are full loops — **regenerate** them. Background must be 100% transparent (alpha=0), no shadow/prop/text.

## Quota / errors
`/catalog`, `/transparent`, `/describe` call OpenAI. If OpenAI billing is exhausted they return **`429 insufficient_quota`** (the caller/proxy may surface it as 502). Fix = add OpenAI credit; no code change. `/embed/*` does NOT use OpenAI (local OpenCLIP) so it keeps working regardless.

## Auth (TWO schemes — deliberate)
- OpenAI endpoints (`/catalog`, `/transparent`, `/describe`): header `x-api-key: <AI_FEATURES_API_KEY>` (only enforced if that env is set).
- `/embed/*`: header `Authorization: Bearer <EMBEDDER_API_KEY>` — **identical to the old embedder**, so Jewel Factory's existing embedder client works with zero code change. Falls back to `AI_FEATURES_API_KEY`.

## Env
| Var | Required | Notes |
|---|---|---|
| `OPENAI_API_KEY` | ✅ for catalog/transparent/describe | gpt-image-2 + gpt-4o |
| `AI_FEATURES_API_KEY` | optional | x-api-key for OpenAI endpoints |
| `EMBEDDER_API_KEY` | optional | Bearer for `/embed/*` (falls back to AI_FEATURES_API_KEY) |
| `AI_FEATURES_ALLOWED_ORIGINS` | optional | CSV; default `*` |
| `CATALOG_MODEL` / `TRANSPARENT_MODEL` / `TRANSPARENT_BG_MODEL` / `DESCRIBE_MODEL` | optional | defaults gpt-image-2 / gpt-image-2 / gpt-image-1 / gpt-4o. `TRANSPARENT_BG_MODEL` must support `background="transparent"` (gpt-image-1). |
| `HF_HOME` | (Docker sets) | `/data/.huggingface` — CLIP model cache |

## Deploy (HF Docker Space)
1. Space → SDK Docker → push this repo. HF builds the Dockerfile, serves on 7860.
2. Space Settings → Variables → `OPENAI_API_KEY` (+ `EMBEDDER_API_KEY` if used).
3. Verify `GET /health` → `{"ok":true,"service":"ai-features","openai":true}`.
4. Jewel Factory: set `AI_FEATURES_URL` = this Space, and point `EMBEDDER_URL` here too.

**Current deployment:** live at HF Space `Botivate2026/ai-workspace` →
`https://botivate2026-ai-workspace.hf.space` (health verified). Use the
**lowercase** host in `AI_FEATURES_URL`/`EMBEDDER_URL` — a capital-cased URL
307-redirects and drops the POST body (→ upstream 502). **Blocker:** the
OpenAI-backed endpoints (`/catalog`, `/transparent`, `/describe`) currently return
`429 insufficient_quota` — add OpenAI billing/credit (or set a funded
`OPENAI_API_KEY` on the Space + restart). `/embed/*` uses local OpenCLIP and is
unaffected. `AI_FEATURES_API_KEY` is NOT set on the Space, so leave it empty on
Render too (no `x-api-key` sent).

## Gotchas
- **OpenCLIP model (~350 MB) is LAZY-LOADED** on the first `/embed` call (not at boot),
  so `/catalog`/`/describe` stay fast. First `/embed` after a cold Space takes ~30–90s.
- **The catalog/transparent prompts are tuned + proven** (ported verbatim from the
  Colab pipeline). Don't casually reword them.
- **`/embed/*` must keep the old embedder's contract** (path, multipart `file`,
  `{embedding}` shape, Bearer auth) — Jewel Factory depends on it unchanged.
- **`verify_and_center`** crops the generated PNG to its non-transparent bbox and
  re-pads to a centered square, so AR pivot calibration stays consistent. Keep it.
- **No CUDA on HF free** — torch is CPU-only (installed via the pytorch CPU index in the Dockerfile).
- Every image call = a paid OpenAI request; regenerate is one call per click for `/catalog`/`/describe`, but **`/transparent` is 2 calls per click** (position + transparency step) — roughly double cost/latency, intended trade-off for reliable transparency.

## Add a future AI feature
1. `routes/<feature>.py` with an `APIRouter` + endpoint.
2. `main.py`: `app.include_router(<feature>_router, dependencies=[Depends(require_key)])`
   (or its own auth if it needs a different scheme, like `/embed/*`).
3. Redeploy. Same URL, same key. Jewel Factory calls the new path at `AI_FEATURES_URL`.

## Integration with Jewel Factory
Jewel Factory proxies these server-side (`lib/api/routes/manufacturer-ai.ts` →
`/api/manufacturer/ai/{describe,catalog,transparent}`) so the browser never sees
the service URL/key. See `INTEGRATION.md`.
