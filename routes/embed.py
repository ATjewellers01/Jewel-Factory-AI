"""
/embed/* — OpenCLIP (ViT-B-32 / laion2b_s34b_b79k, 512-d) image/text embeddings
for visual search. Ported verbatim from the standalone embedder Space so Jewel
Factory works unchanged (same paths, same response shapes, same Bearer auth).

The model is HEAVY (torch + ~350 MB weights). It is LAZY-LOADED on the first
/embed call, so the light OpenAI endpoints (/catalog, /transparent, /describe)
stay fast and don't wait for the model at boot.

Auth: this router uses `Authorization: Bearer <EMBEDDER_API_KEY>` (matches Jewel
Factory's existing embedder client). Set EMBEDDER_API_KEY (falls back to
AI_FEATURES_API_KEY). The main app's x-api-key guard is NOT applied here.
"""
from __future__ import annotations

import io
import os
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel, Field

CLIP_MODEL = "ViT-B-32"
CLIP_PRETRAINED = "laion2b_s34b_b79k"
EMBEDDING_DIM = 512

# Bearer key — same env Jewel Factory already sends. Fall back to the shared key.
EMBED_API_KEY = os.environ.get("EMBEDDER_API_KEY") or os.environ.get("AI_FEATURES_API_KEY")

router = APIRouter()


# ── Lazy model singleton ─────────────────────────────────────────────────────
class _Embedder:
    def __init__(self) -> None:
        import torch
        import open_clip
        self._torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[OpenCLIP] Loading {CLIP_MODEL} ({CLIP_PRETRAINED}) on {self.device}…")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            CLIP_MODEL, pretrained=CLIP_PRETRAINED, device=self.device
        )
        self.model.eval()
        self.tokenizer = open_clip.get_tokenizer(CLIP_MODEL)
        print("[OpenCLIP] Ready.")

    def _to_tensor(self, raw: bytes):
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        return self.preprocess(image).unsqueeze(0).to(self.device)

    def embed_image(self, raw: bytes) -> np.ndarray:
        t = self._to_tensor(raw)
        with self._torch.no_grad():
            f = self.model.encode_image(t)
        return _l2(f.cpu().numpy().flatten().astype(np.float32))

    def embed_image_batch(self, raws: List[bytes]) -> List[Optional[np.ndarray]]:
        tensors, valid, out = [], [], [None] * len(raws)
        for i, raw in enumerate(raws):
            try:
                tensors.append(self._to_tensor(raw)); valid.append(i)
            except Exception as exc:
                print(f"[OpenCLIP] skip image {i}: {exc}")
        if not tensors:
            return out
        batch = self._torch.cat(tensors, dim=0)
        with self._torch.no_grad():
            f = self.model.encode_image(batch)
        emb = f.cpu().numpy().astype(np.float32)
        for j, idx in enumerate(valid):
            out[idx] = _l2(emb[j])
        return out

    def embed_text(self, text: str) -> np.ndarray:
        tok = self.tokenizer([text]).to(self.device)
        with self._torch.no_grad():
            f = self.model.encode_text(tok)
        return _l2(f.cpu().numpy().flatten().astype(np.float32))


def _l2(vec: np.ndarray) -> np.ndarray:
    return vec / (np.linalg.norm(vec) + 1e-10)


_singleton: _Embedder | None = None


def _get() -> _Embedder:
    global _singleton
    if _singleton is None:
        _singleton = _Embedder()  # first call pays the model-load cost
    return _singleton


# ── Auth (Bearer — identical to the old embedder / what Jewel Factory sends) ──
def require_bearer(authorization: Optional[str] = Header(default=None)) -> None:
    if not EMBED_API_KEY:
        return  # open in dev
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    if authorization.removeprefix("Bearer ") != EMBED_API_KEY:
        raise HTTPException(401, "Invalid bearer token")


# ── Schemas (same shape as the old embedder) ─────────────────────────────────
class EmbedResponse(BaseModel):
    dim: int = Field(default=EMBEDDING_DIM)
    embedding: List[float]


class BatchEmbedResponse(BaseModel):
    dim: int = Field(default=EMBEDDING_DIM)
    embeddings: List[Optional[List[float]]]


class TextBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


# ── Routes (paths identical to the old embedder) ─────────────────────────────
@router.post("/embed/image", response_model=EmbedResponse, dependencies=[Depends(require_bearer)])
async def embed_image(file: UploadFile = File(...)) -> EmbedResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty file")
    try:
        vec = _get().embed_image(raw)
    except Exception as exc:
        raise HTTPException(422, f"Cannot decode image: {exc}")
    return EmbedResponse(embedding=vec.tolist())


@router.post("/embed/image/batch", response_model=BatchEmbedResponse, dependencies=[Depends(require_bearer)])
async def embed_image_batch(files: List[UploadFile] = File(...)) -> BatchEmbedResponse:
    if not files:
        raise HTTPException(400, "No files uploaded")
    raws = [await f.read() for f in files]
    vectors = _get().embed_image_batch(raws)
    return BatchEmbedResponse(embeddings=[v.tolist() if v is not None else None for v in vectors])


@router.post("/embed/text", response_model=EmbedResponse, dependencies=[Depends(require_bearer)])
def embed_text(body: TextBody) -> EmbedResponse:
    return EmbedResponse(embedding=_get().embed_text(body.text).tolist())


@router.post("/embed/hybrid", response_model=EmbedResponse, dependencies=[Depends(require_bearer)])
async def embed_hybrid(
    text: Optional[str] = Form(default=None),
    weight: float = Form(default=0.5),
    file: Optional[UploadFile] = File(default=None),
) -> EmbedResponse:
    if text is None and file is None:
        raise HTTPException(400, "Provide text, file, or both")
    if weight < 0 or weight > 1:
        raise HTTPException(400, "weight must be in [0, 1]")
    e = _get()
    tv = e.embed_text(text) if text else None
    iv = None
    if file is not None:
        raw = await file.read()
        if raw:
            try:
                iv = e.embed_image(raw)
            except Exception as exc:
                raise HTTPException(422, f"Cannot decode image: {exc}")
    if tv is not None and iv is not None:
        vec = _l2(weight * tv + (1.0 - weight) * iv)
    elif tv is not None:
        vec = tv
    else:
        assert iv is not None
        vec = iv
    return EmbedResponse(embedding=vec.tolist())
