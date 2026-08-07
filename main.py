"""
AI-Features — one Python service for ALL Jewel Factory AI features.

Deploy ONCE (like the embedder). Each feature is a route module under routes/;
adding a future feature = a new route file + one include_router line here. The
Jewel Factory app calls this at $AI_FEATURES_URL.

Current endpoints:
  POST /catalog       raw image            -> luxury studio catalog image (base64 PNG)
  POST /classify       raw image            -> best-guess { category, subCategory, confident }
  POST /transparent   raw image + type     -> background-free centered try-on PNG (base64)
  POST /describe      image + specs        -> { designName, description }
  POST /embed/image | /embed/text | /embed/hybrid | /embed/image/batch  -> OpenCLIP 512-d vectors
  GET  /health        liveness

Auth:
  - OpenAI endpoints (/catalog, /classify, /transparent, /describe): x-api-key: <AI_FEATURES_API_KEY> (if set).
  - /embed/* (visual search): Authorization: Bearer <EMBEDDER_API_KEY> — same as before,
    so Jewel Factory's existing embedder client works unchanged. Just point its
    EMBEDDER_URL at THIS service.
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from lib.config import API_KEY
from routes.catalog import router as catalog_router
from routes.classify import router as classify_router
from routes.transparent import router as transparent_router
from routes.describe import router as describe_router
from routes.embed import router as embed_router

app = FastAPI(title="Jewel Factory AI-Features", version="1.0.0")

ALLOWED = [o.strip() for o in os.environ.get("AI_FEATURES_ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def require_key(x_api_key: str | None = Header(default=None)):
    # No key configured → open (dev). Key configured → must match.
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "Invalid or missing x-api-key.")


@app.get("/health")
def health():
    return {"ok": True, "service": "ai-features", "openai": bool((os.environ.get("OPENAI_API_KEY") or "").strip())}


# OpenAI feature routers — gated by the optional shared x-api-key.
app.include_router(catalog_router, dependencies=[Depends(require_key)])
app.include_router(classify_router, dependencies=[Depends(require_key)])
app.include_router(transparent_router, dependencies=[Depends(require_key)])
app.include_router(describe_router, dependencies=[Depends(require_key)])

# Embedding router — uses its OWN Bearer auth (matches Jewel Factory's client).
# No x-api-key guard here so the existing embedder contract is unchanged.
app.include_router(embed_router)
