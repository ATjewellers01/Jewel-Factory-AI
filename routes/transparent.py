"""
/transparent — raw jewellery photo -> background-free, centered try-on PNG.
Verbatim logic from the Colab pipeline (gpt-image edit + AR position prompt),
then verify_and_center so pivot calibration stays consistent for the AR engine.
`jewelleryType`: necklace | earring_left | earring_right | ring_index | ring_middle | bangle
"""
from __future__ import annotations

import base64
import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from lib.config import openai_client, TRANSPARENT_MODEL
from lib.prompts import build_ar_prompt
from lib.image_utils import normalize_to_png, verify_and_center

router = APIRouter()


@router.post("/transparent")
async def transparent(image: UploadFile = File(...), jewelleryType: str = Form("necklace"), extraInstructions: str = Form("")):
    raw = await image.read()
    if not raw:
        raise HTTPException(400, "Empty image.")
    try:
        png = normalize_to_png(raw)
    except Exception as e:
        raise HTTPException(400, f"Bad image: {e}")

    try:
        client = openai_client()
        result = client.images.edit(
            model=TRANSPARENT_MODEL,
            image=("source_image.png", io.BytesIO(png), "image/png"),
            prompt=build_ar_prompt(jewelleryType, extraInstructions),
            size="1024x1024",
        )
        gen = base64.b64decode(result.data[0].b64_json)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Transparent generation failed: {e}")

    try:
        centered = verify_and_center(gen)
    except ValueError as e:
        raise HTTPException(502, str(e))

    return {"imageBase64": base64.b64encode(centered).decode(), "mimeType": "image/png"}
