---
title: AI Features
emoji: 💎
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Jewel Factory AI (catalog + transparent PNG + name/description + visual-search embeddings)
---

# Jewel Factory — AI-Features Service

**ONE Python service for ALL Jewel Factory AI.** Deploy once; every feature is an
endpoint. Includes the OpenCLIP embedder (visual search) — so there's a **single URL**.
New AI feature later = new route file + one line in `main.py` — no new deployment.

## Endpoints

| Method | Path | Input | Output |
|---|---|---|---|
| POST | `/catalog` | `image` + optional `extraInstructions` | `{ imageBase64 }` — luxury studio catalog image |
| POST | `/transparent` | `image` + `jewelleryType` + optional `extraInstructions` | `{ imageBase64 }` — transparent try-on PNG (**2 OpenAI calls internally** — see below) |
| POST | `/describe` | `image` + `category,subCategory,weight,purity` + optional `extraInstructions` | `{ designName, description }` |
| POST | `/embed/image` · `/embed/text` · `/embed/hybrid` · `/embed/image/batch` | image/text | `{ dim, embedding }` — OpenCLIP 512-d (visual search) |
| GET | `/health` | — | liveness |

`jewelleryType`: necklace · earring_left · earring_right · ring_index · ring_middle · bangle
`extraInstructions` = the manufacturer's **regenerate** instruction (e.g. "simpler background") — optional; empty = default.

**`/transparent` is a 2-step pipeline, not one call:** Step 1 (`TRANSPARENT_MODEL`,
default `gpt-image-2`) positions the product on a plain grey background; Step 2
(`TRANSPARENT_BG_MODEL`, default `gpt-image-1`) uses the native
`background="transparent"` param to strip that grey to real alpha transparency.
`gpt-image-1` is the only model confirmed to support that param — and it's
**retiring 2026-10-23**, so `TRANSPARENT_BG_MODEL` will need repointing before then.
See `CLAUDE.md` for the full rationale and cost breakdown.

## Env

| Var | Required | Notes |
|---|---|---|
| `OPENAI_API_KEY` | ✅ (for catalog/transparent/describe) | OpenAI key (gpt-image-2, gpt-image-1, gpt-4o) |
| `AI_FEATURES_API_KEY` | optional | If set, `/catalog /transparent /describe` need `x-api-key: <key>` |
| `EMBEDDER_API_KEY` | optional | Bearer key for `/embed/*` (same as before). Falls back to `AI_FEATURES_API_KEY`. |
| `AI_FEATURES_ALLOWED_ORIGINS` | optional | CSV; default `*` |
| `CATALOG_MODEL` / `TRANSPARENT_MODEL` / `TRANSPARENT_BG_MODEL` / `DESCRIBE_MODEL` | optional | defaults gpt-image-2 / gpt-image-2 / **gpt-image-1** / gpt-4o |

## Cost (verified 2026-07-23 OpenAI pricing, ≈ ₹96.6/$)

No route sets `quality=` explicitly (only `size="1024x1024"`), so all image calls
run on OpenAI's default `quality="auto"` — for our detailed, multi-instruction
prompts this resolves to **High** in practice. A full "Generate All" (describe +
catalog + both transparent steps, 4 OpenAI calls) costs **≈ $0.59 (≈ ₹57)** at High,
≈ $0.15 (≈ ₹15) if `quality="medium"` were forced. Regenerate-Try-On alone (2 calls)
is the priciest single button: ≈ ₹36 (High) / ₹9 (Medium). Full breakdown +
per-prompt token sizes: `CLAUDE.md` → "Cost per generation".

## Auth (two schemes, on purpose)
- OpenAI endpoints → `x-api-key: <AI_FEATURES_API_KEY>` (if set).
- `/embed/*` → `Authorization: Bearer <EMBEDDER_API_KEY>` — **identical to the old
  embedder**, so Jewel Factory's existing client works with zero code change.

## Migrating from the old embedder Space (one URL now)
The OpenCLIP model + `/embed/*` are baked into THIS service. To switch Jewel Factory:
1. Deploy this Space, set `OPENAI_API_KEY` (+ `EMBEDDER_API_KEY` if you used one).
2. On Render, change **`EMBEDDER_URL`** to this Space's URL (and add `AI_FEATURES_URL`
   = same URL). No JF code change — same `/embed/image` contract.
3. The old embedder Space can be paused/deleted.

> The OpenCLIP model (~350 MB) loads **lazily on the first `/embed` call**, so
> `/catalog`, `/transparent`, `/describe` stay fast and don't wait at boot.

## Deploy (Hugging Face Docker Space — same as embedder)

1. Create a Space → SDK **Docker**.
2. Push this folder (git). HF builds the Dockerfile, serves on **7860**.
3. Space → Settings → Variables → set `OPENAI_API_KEY` (+ optional `AI_FEATURES_API_KEY`).
4. Verify `GET /health` → `{"ok":true,"openai":true}`.

The Jewel Factory app points `AI_FEATURES_URL` at this Space. See `INTEGRATION.md`.

## Run locally
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python -m uvicorn main:app --port 7860
```

## Add a future AI feature
1. `routes/<feature>.py` with an `APIRouter` + your endpoint.
2. `main.py`: `app.include_router(<feature>_router, dependencies=[Depends(require_key)])`.
3. Redeploy. Same URL, same key — no separate service.
