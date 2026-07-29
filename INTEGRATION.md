# Integration — Jewel Factory ↔ AI-Features

The Jewel Factory app (Next.js) calls this Python service for AI features. Same
model as the embedder: one env var points at the deployed Space.

## 1. Env in Jewel Factory (ONE URL for everything)
```
AI_FEATURES_URL=https://<user>-ai-features.hf.space
AI_FEATURES_API_KEY=            # only if you set one on the service (x-api-key)

# Visual search now lives in the SAME service — point the existing var here:
EMBEDDER_URL=https://<user>-ai-features.hf.space   # same URL; JF calls /embed/image on it
EMBEDDER_API_KEY=               # keep whatever you used before (Bearer)
```
Add `AI_FEATURES_URL` to `lib/env.ts` (optional, like EMBEDDER_URL) and to `.env`.
`EMBEDDER_URL` already exists — just change its value to this Space. Old embedder
Space can be retired.

## 2. Where it's used — Manufacturer "Add Design"
In `components/manufacturer/ProductForm.tsx`, add a **"✨ Generate with AI"** flow
after the manufacturer picks a raw photo + category/sub-category/weight/purity:

1. **Describe** (description only — design names were removed from Jewel Factory
   2026-07-30; the auto design number is the sole product identifier now):
   `POST {AI_FEATURES_URL}/describe` (multipart: `image`, `category`, `subCategory`, `weight`, `purity`)
   → `{ description }` → prefill the form's Description field.
2. **Catalog image**:
   `POST {AI_FEATURES_URL}/catalog` (multipart: `image`)
   → `{ imageBase64 }` → upload that PNG to S3 (existing product-image flow)
   → save as the product's catalog image.
3. **Transparent try-on PNG**:
   `POST {AI_FEATURES_URL}/transparent` (multipart: `image`, `jewelleryType`)
   → `{ imageBase64 }` → upload to S3 (tryon bucket) → set `has_tryon=true`.

The manufacturer reviews/edits everything, then Saves as normal. Nothing is
auto-committed — AI just prefills.

> Server-side proxy recommended: add a small Next.js API route (e.g.
> `/api/manufacturer/ai/*`) that forwards to `AI_FEATURES_URL` with the
> `x-api-key` header, so the OpenAI-backed service key never touches the browser.

## 3. Cost / UX notes
- gpt-image edits take a few seconds each — show a spinner; generate on demand
  (a button), not on every keystroke.
- If `AI_FEATURES_URL` is unset, hide the "Generate with AI" button — manual add
  still works exactly as today.

## 4. Future AI features
Everything AI lives in THIS service. To add one (e.g. design-ranking, style tags):
new `routes/<x>.py` + one `include_router` line in `main.py`, redeploy. Jewel
Factory calls the new path at the same `AI_FEATURES_URL`. No new deployment, no
new env var.
