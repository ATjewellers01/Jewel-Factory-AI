"""
/classify — raw jewellery photo -> best-guess { category, subCategory } from
the exact Jewel Factory taxonomy. Used by Jewel Factory's similar-design
search: a customer/retailer uploads a raw photo with no category picker, but
/catalog (the background-cleanup step run before embedding) gives noticeably
better, more faithful results when it knows the category. This endpoint is
the missing piece — a category GUESS derived from the image itself, not a
description generator (that's /describe, which goes the other way: category
provided -> ad copy out).

Returns confident=false (with category/subCategory left null) when the model
itself is unsure or the image is too unclear to tell — callers should treat
that as "ask for a clearer photo," not silently fall back to a wrong guess.
"""
from __future__ import annotations

import base64
import json

from fastapi import APIRouter, File, HTTPException, UploadFile

from lib.config import openai_client, DESCRIBE_MODEL
from lib.image_utils import normalize_to_png

router = APIRouter()

# Kept in sync with lib/categories.ts's CATEGORY_TREE on the Jewel Factory
# side — this is a display list for the prompt, not a shared import (cross-
# repo, Python vs TypeScript), so if the taxonomy changes there, update here too.
CATEGORY_TREE = {
    "Bangles": [
        "Top Seller Bangles", "Premium Bangles", "Ultra Light Bangles", "Fancy Hmade Bangles",
        "Fusion Bangles", "Antique Bangles", "Baby Bangles", "Gajra Bangles", "Hollow Pipe Bangles",
        "Indo Italian Bangles", "Machine Bangles", "Plaster Bangles", "Raji Bangles",
        "V- Pacheli Bangles", "Nakshi Bangles",
    ],
    "Bindiya / Mangtika": [],
    "Bracelet": ["Gents Bracelet / Kada", "Ladies Bracelet"],
    "Chain": [],
    "Ear Chain Kannoti": [],
    "Earrings": ["Chandbali", "Jhumki", "Kannoti Earring", "Tops", "V Chain Earring"],
    "JF Coin": [],
    "Mangalsutra": [],
    "Men's Collection": ["Belt Buckle", "Cufflinks"],
    "Nath / Nose Ring": [],
    "Pendants": ["Dorla Pendants", "Double Hook Pendants", "Single Hook Pendants"],
    "Rings": ["Couple Ring", "Gents Ring", "Ladies Ring"],
    "Set": ["Antique Set", "Chain Set", "Choker Set", "Long Set", "Pendent Set", "Short Set", "Turkish Set"],
    "Watch": ["Gents Watch", "Ladies Watch"],
}


def _build_classify_prompt() -> str:
    lines = []
    for category, subs in CATEGORY_TREE.items():
        if subs:
            lines.append(f'- "{category}": {", ".join(subs)}')
        else:
            lines.append(f'- "{category}" (no sub-categories)')
    tree_text = "\n".join(lines)
    return (
        "You are classifying a jewellery photo into an EXACT taxonomy. Look at the "
        "image and pick the single best-matching category, and sub-category if the "
        "category has one.\n\n"
        f"Allowed categories and their sub-categories:\n{tree_text}\n\n"
        "Return ONLY strict JSON with these keys:\n"
        '  "category": one of the exact category strings above, or null if you cannot '
        "tell what kind of jewellery this is (blurry, not jewellery, or ambiguous)\n"
        '  "subCategory": one of that category\'s exact sub-category strings above, or '
        "null if the category has no sub-categories or you're not sure which one\n"
        '  "confident": true only if you are reasonably sure of the category (sub-category '
        "confidence doesn't need to be as high)\n\n"
        "Do NOT invent a category or sub-category that isn't in the list above. If the "
        "image is unclear, cropped too tight to tell, or not jewellery at all, set "
        'confident to false and category to null.\n\n'
        'Example: {"category": "Bangles", "subCategory": "Fancy Hmade Bangles", "confident": true}'
    )


@router.post("/classify")
async def classify(image: UploadFile = File(...)):
    raw = await image.read()
    if not raw:
        raise HTTPException(400, "Empty image.")
    try:
        png = normalize_to_png(raw)
    except Exception as e:
        raise HTTPException(400, f"Bad image: {e}")

    data_url = f"data:image/png;base64,{base64.b64encode(png).decode()}"

    try:
        client = openai_client()
        resp = client.chat.completions.create(
            model=DESCRIBE_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _build_classify_prompt()},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=200,
        )
        content = resp.choices[0].message.content or "{}"
        parsed = json.loads(content)
    except RuntimeError as e:  # no API key
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Classification failed: {e}")

    category = parsed.get("category")
    sub_category = parsed.get("subCategory")
    confident = bool(parsed.get("confident"))

    # Guard against a hallucinated category/sub-category outside the taxonomy —
    # treat that the same as "not confident" rather than passing a bogus value
    # on to /catalog's category-specific prompt branch.
    if category not in CATEGORY_TREE:
        category = None
        confident = False
    elif sub_category not in CATEGORY_TREE.get(category, []):
        sub_category = None

    return {"category": category, "subCategory": sub_category, "confident": confident}
