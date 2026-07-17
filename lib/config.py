"""
Shared config for the AI-Features service.

One service, many endpoints (catalog, transparent, describe, ... future). Every
feature reuses this OpenAI client + auth so we deploy ONCE (like the embedder)
and just add a new route file per feature.
"""
from __future__ import annotations

import os

from openai import OpenAI

# ── OpenAI ───────────────────────────────────────────────────────────────────
_OPENAI_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()

_client: OpenAI | None = None


def openai_client() -> OpenAI:
    """Lazily build the OpenAI client (so the service boots even before a key is
    set — endpoints then return a clear 503 instead of crashing at import)."""
    global _client
    if not _OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set on this service.")
    if _client is None:
        _client = OpenAI(api_key=_OPENAI_KEY)
    return _client


# ── Service auth (optional shared key, same idea as EMBEDDER_API_KEY) ─────────
API_KEY = os.environ.get("AI_FEATURES_API_KEY")

# Image models (kept identical to the working Colab pipeline).
CATALOG_MODEL = os.environ.get("CATALOG_MODEL", "gpt-image-2")
TRANSPARENT_MODEL = os.environ.get("TRANSPARENT_MODEL", "gpt-image-2")
DESCRIBE_MODEL = os.environ.get("DESCRIBE_MODEL", "gpt-4o")
