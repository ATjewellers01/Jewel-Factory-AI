"""
/describe — image + specs (category, sub-category, weight, purity) -> auto
designName + website description. Uses a vision model (gpt-4o) and returns JSON.
"""
from __future__ import annotations

import base64
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from lib.config import openai_client, DESCRIBE_MODEL
from lib.prompts import build_describe_prompt
from lib.image_utils import normalize_to_png

router = APIRouter()


@router.post("/describe")
async def describe(
    image: UploadFile = File(...),
    category: str = Form(""),
    subCategory: str = Form(""),
    weight: str = Form(""),
    purity: str = Form(""),
    extraInstructions: str = Form(""),
):
    raw = await image.read()
    if not raw:
        raise HTTPException(400, "Empty image.")
    try:
        png = normalize_to_png(raw)
    except Exception as e:
        raise HTTPException(400, f"Bad image: {e}")

    data_url = f"data:image/png;base64,{base64.b64encode(png).decode()}"
    prompt = build_describe_prompt(category, subCategory, weight, purity, extraInstructions)

    try:
        client = openai_client()
        resp = client.chat.completions.create(
            model=DESCRIBE_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=400,
        )
        content = resp.choices[0].message.content or "{}"
        parsed = json.loads(content)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Describe failed: {e}")

    name = str(parsed.get("designName", "")).strip()
    desc = str(parsed.get("description", "")).strip()
    if not name and not desc:
        raise HTTPException(502, "Model returned no name/description.")
    return {"designName": name, "description": desc}
