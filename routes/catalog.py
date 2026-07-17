"""
/catalog — raw jewellery photo -> attractive luxury studio catalog image.
Verbatim logic from the proven Colab pipeline (gpt-image edit + CATALOG_PROMPT).
Returns the image as base64 PNG so the caller (Jewel Factory) can upload it to
Cloudinary and save the URL.
"""
from __future__ import annotations

import base64
import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from lib.config import openai_client, CATALOG_MODEL
from lib.prompts import build_catalog_prompt
from lib.image_utils import normalize_to_png

router = APIRouter()


@router.post("/catalog")
async def catalog(image: UploadFile = File(...), extraInstructions: str = Form("")):
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
            model=CATALOG_MODEL,
            image=("source_image.png", io.BytesIO(png), "image/png"),
            prompt=build_catalog_prompt(extraInstructions),
            size="1024x1024",
        )
        b64 = result.data[0].b64_json
    except RuntimeError as e:  # no API key
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Catalog generation failed: {e}")

    return {"imageBase64": b64, "mimeType": "image/png"}
