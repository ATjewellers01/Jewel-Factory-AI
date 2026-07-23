"""
/transparent — raw jewellery photo -> background-free, centered try-on PNG.
2-step pipeline, verbatim from the proven Colab notebook:
  Step 1 (gpt-image-2): position the product on a plain grey background.
  Step 2 (gpt-image-1 + background="transparent"): strip that grey background
    to real alpha transparency via the native API param — more reliable than
    asking for transparency in the prompt alone (the single-step version of
    this endpoint sometimes shipped an opaque black background instead).
Then verify_and_center so pivot calibration stays consistent for the AR engine.
`jewelleryType`: necklace | earring_left | earring_right | ring_index | ring_middle | bangle
"""
from __future__ import annotations

import base64
import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from lib.config import openai_client, TRANSPARENT_MODEL, TRANSPARENT_BG_MODEL
from lib.prompts import build_ar_position_prompt, build_ar_transparency_prompt
from lib.image_utils import normalize_to_png, verify_and_center

router = APIRouter()


@router.post("/transparent")
async def transparent(image: UploadFile = File(...), jewelleryType: str = Form("necklace"), extraInstructions: str = Form(""), category: str = Form(""), subCategory: str = Form("")):
    raw = await image.read()
    if not raw:
        raise HTTPException(400, "Empty image.")
    try:
        png = normalize_to_png(raw)
    except Exception as e:
        raise HTTPException(400, f"Bad image: {e}")

    try:
        client = openai_client()

        # Step 1 — position on a plain grey background (gpt-image-2)
        step1 = client.images.edit(
            model=TRANSPARENT_MODEL,
            image=("source_image.png", io.BytesIO(png), "image/png"),
            prompt=build_ar_position_prompt(jewelleryType, extraInstructions, category, subCategory),
            size="1024x1024",
        )
        step1_bytes = base64.b64decode(step1.data[0].b64_json)

        # Step 2 — strip the grey background to real transparency (gpt-image-1)
        step2 = client.images.edit(
            model=TRANSPARENT_BG_MODEL,
            image=("step1_positioned.png", io.BytesIO(step1_bytes), "image/png"),
            prompt=build_ar_transparency_prompt(),
            background="transparent",
            size="1024x1024",
        )
        gen = base64.b64decode(step2.data[0].b64_json)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Transparent generation failed: {e}")

    try:
        centered = verify_and_center(gen)
    except ValueError as e:
        raise HTTPException(502, str(e))

    return {"imageBase64": base64.b64encode(centered).decode(), "mimeType": "image/png"}
