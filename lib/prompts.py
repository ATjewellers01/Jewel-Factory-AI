"""
Prompts — ported verbatim from the proven Colab pipeline (catalog + AR position),
plus a describe prompt for auto name + description. Don't casually reword these:
the image prompts are tuned and working.
"""

import random

# ── AR / transparent try-on: 2-step pipeline (matches the proven Colab notebook) ─
# Step 1 (gpt-image-2): position the product correctly, on a PLAIN GREY
# background (not transparent yet) — simple/high-contrast so step 2 can key
# it out cleanly. Step 2 (gpt-image-1 + background="transparent" API param):
# ONLY strips the background to real alpha transparency, no repositioning.
POSITION_INSTRUCTIONS = {
    "necklace": (
        "This asset is for a 2D virtual try-on that overlays ONTO a person's neck "
        "and chest from the front, so show ONLY the front-facing worn drape of the "
        "necklace as it would appear resting on the collarbone/chest — the central "
        "pendant, bib, and the two front strands curving up toward the shoulders. "
        "DO NOT show the rear/back neck chain, the strand that goes behind the neck, "
        "or the clasp — omit the entire back loop; the top should be an open U/V shape, "
        "NOT a closed circle. Photograph it straight-on from the front (not tilted), "
        "centered horizontally, with the two open strand ends reaching the top-left and "
        "top-right of the frame."
    ),
    "earring_left": (
        "Show a single earring photographed straight-on from the front. "
        "Position it in the right-center of the frame (since this earring "
        "will render on the wearer's left ear, camera-left = wearer's right "
        "in a mirrored view). Hook or post should point upward, top of frame."
    ),
    "earring_right": (
        "Show a single earring photographed straight-on from the front. "
        "Position it in the left-center of the frame. Hook or post should "
        "point upward, top of frame."
    ),
    "ring_index": (
        "Show the ring photographed from directly above/front, band facing "
        "the viewer, centered exactly in the middle of the frame, "
        "front-facing top-down view as if worn on an index finger."
    ),
    "ring_middle": (
        "Show the ring photographed from directly above/front, band facing "
        "the viewer, centered exactly in the middle of the frame."
    ),
    "bangle": (
        "This asset is for a 2D virtual try-on that overlays flat onto a wrist, so "
        "show the bangle/bracelet as a FLAT, STRAIGHT horizontal band — laid out "
        "fully open, edge-to-edge across the frame, with its complete front design "
        "visible along the entire length. DO NOT show it as a curved arc, an oval, "
        "or any closed/circular ring shape — it must be perfectly straight and flat, "
        "as if unrolled and photographed directly from the front. Center it "
        "horizontally and vertically in the frame with even padding on left and right."
    ),
}

# Step 1 (positioning): plain grey background, NOT transparent — that's step 2's job.
AR_POSITION_BASE_INSTRUCTION = (
    "Do not redesign, resize, or alter the jewellery's shape, gemstones, "
    "engravings, or proportions — preserve the exact product exactly as "
    "photographed. Place it on a plain flat solid light-grey (#e0e0e0) "
    "background with no props, no shadow, no reflection, no watermark, "
    "no border. The product must fill 70-85% of the frame with even "
    "padding on all sides."
)

# Step 2 (transparency only): takes step 1's grey-background output, removes it.
# No positioning language here — step 1 already handled that.
AR_TRANSPARENCY_INSTRUCTION = (
    "Remove the background completely, leaving 100% transparent pixels "
    "(alpha=0) everywhere except the jewellery product itself. Do not "
    "redesign, resize, recolor, or alter the jewellery in any way — only "
    "delete the background. No shadow, no reflection, no watermark, no "
    "border, no added background of any kind."
)


def _with_extra(prompt: str, extra: str | None) -> str:
    """Append the manufacturer's regenerate instruction, if any."""
    extra = (extra or "").strip()
    if not extra:
        return prompt
    return f"{prompt}\n\nADDITIONAL INSTRUCTION FROM THE USER (follow it while keeping the product exact): {extra}"


def build_ar_position_prompt(jtype: str, extra: str | None = None, category: str | None = None, sub_category: str | None = None) -> str:
    """Step 1 — position the product on a plain grey background."""
    pos = POSITION_INSTRUCTIONS.get(jtype, POSITION_INSTRUCTIONS["necklace"])
    return _with_extra(f"{pos} {AR_POSITION_BASE_INSTRUCTION}", extra)


def build_ar_transparency_prompt() -> str:
    """Step 2 — strip the step-1 output's grey background to real transparency."""
    return AR_TRANSPARENCY_INSTRUCTION


def _category_background_guidance(category: str | None, sub_category: str | None = None) -> str:
    """Return category + sub-category specific background guidance for themed catalog styling.

    Uses EXACT categories from lib/categories.ts (CATEGORY_TREE) to ensure
    consistency with the manufacturer form dropdowns.
    """
    if not category:
        return ""

    category_lower = category.lower()
    sub_category_lower = (sub_category or "").lower()

    # Backgrounds mapped to ACTUAL categories + SUB-CATEGORIES from CATEGORY_TREE
    # Every sub-category from lib/categories.ts has its own themed guidance
    backgrounds = {
        "bangles": {
            "default": "Use a wrist form or elegant stand on a soft fabric surface (ivory, cream, or marble) with warm lighting that emphasizes curves, texture, and movement.",
            "themes": {
                "18k bangles": "Use rich, warm lighting highlighting premium quality, intricate detailing, and luxurious 18K gold finish.",
                "antique bangle": "Use dramatic, moody lighting with antique props (vintage fabric, aged wood) emphasizing heritage aesthetic.",
                "baby bangle": "Use delicate, gentle lighting with soft backgrounds showcasing the petite, refined nature of baby bangles.",
                "fancy hmade bangle": "Use vibrant, multi-directional lighting highlighting decorative handmade elements and ornate details.",
                "fusion bangle": "Use balanced lighting combining warm and cool tones to showcase the fusion of traditional and modern designs.",
                "gajra bangle": "Use soft, romantic lighting with floral props emphasizing the bangle's floral-inspired motifs.",
                "hollow bangles": "Use directional side lighting showcasing craftsmanship and creating elegant shadows on hollow design.",
                "indo italian bangle": "Use sophisticated lighting blending warm European and rich Indian aesthetics.",
                "machine bangles": "Use clean, professional lighting emphasizing precision, symmetry, and machine-perfect craftsmanship.",
                "plaster bangle": "Use soft, even lighting that showcases the unique texture and delicate nature of plaster bangles.",
                "reli bangle": "Use warm, layered lighting emphasizing the ornate Reli patterns and detailed craftsmanship.",
                "top seller bangles": "Use showcase lighting that highlights why these are bestsellers—clear, flattering, crowd-pleasing aesthetics.",
                "v- pacheli bangle": "Use elegant, flowing lighting emphasizing the V-shaped Pacheli design and its graceful curves.",
            }
        },
        "earrings": {
            "default": "Use subtle fabric backdrop (silk/velvet in ivory, beige, champagne) with soft side lighting emphasizing details and sparkle.",
            "themes": {
                "chandbali": "Use warm directional lighting highlighting the crescent moon design and ornate detailing.",
                "jhumki": "Use dramatic side lighting with elegant props showcasing jhumki's dangles and movement.",
                "kannoti earring": "Use soft intimate lighting highlighting the chain and ear chain details.",
                "tops": "Use close-up focused lighting emphasizing stud details and gemstone work.",
                "v chain earring": "Use flowing directional lighting showcasing the V-shaped chain design and elegant drape.",
            }
        },
        "rings": {
            "default": "Use luxury ring holder or marble pedestal with focused warm lighting showcasing band details.",
            "themes": {
                "couple ring": "Use paired display with warm matching lighting showcasing complementary designs together.",
                "gents ring": "Use bold strong lighting emphasizing masculine design and substantial presence.",
                "ladies ring": "Use soft romantic lighting with refined props enhancing femininity and delicate details.",
            }
        },
        "set": {
            "default": "Use elegant display setup on soft background with warm even lighting showcasing all pieces as cohesive collection.",
            "themes": {
                "antique set": "Use vintage props and moody warm lighting emphasizing heritage aesthetic of entire collection.",
                "chain set": "Use flowing layout with directional lighting emphasizing chain components and connections.",
                "choker set": "Use close-up intimate lighting emphasizing neckline placement and complete aesthetic.",
                "long set": "Use flowing fabric or full-length display with directional lighting showing length and drape.",
                "pendent set": "Use focused lighting emphasizing pendant as focal point while showcasing companion pieces.",
                "short set": "Use compact focused display with warm lighting highlighting all pieces in unified frame.",
                "turkish set": "Use rich, ornate lighting emphasizing the Turkish design elements and intricate craftsmanship.",
            }
        },
        "bracelet": {
            "default": "Use bracelet stand or graceful display on soft background with warm lighting capturing movement and texture.",
            "themes": {
                "gents bracelet / kada": "Use bold strong lighting emphasizing masculine craftsmanship and substantial design.",
                "ladies bracelet": "Use soft elegant lighting with refined props highlighting delicate details and femininity.",
            }
        },
        "pendants": {
            "default": "Use luxury pendant stand or necklace form with warm focused lighting centering pendant as focal point.",
            "themes": {
                "dorla pendants": "Use directional lighting emphasizing pendant's hanging position and ornate details.",
                "double hook pendants": "Use warm lighting showcasing dual-hook design and balanced aesthetic.",
                "single hook pendants": "Use focused lighting highlighting hook mechanism and main design.",
            }
        },
        "men's collection": {
            "default": "Use bold, professional display with strong masculine lighting showcasing premium craftsmanship.",
            "themes": {
                "belt buckle": "Use focused lighting emphasizing the buckle's design, texture, and masculine presence.",
                "cufflinks": "Use close-up detailed lighting showcasing intricate cufflink design and precious metalwork.",
            }
        },
        "chain": {
            "default": "Use flowing display or elegant drape on soft background with directional lighting highlighting links and craftsmanship.",
        },
        "mangalsutra": {
            "default": "Use luxurious display on soft delicate background with warm intimate lighting emphasizing significance.",
        },
        "nath / nose ring": {
            "default": "Use close-up intimate display with soft lighting emphasizing delicate design and placement.",
        },
        "bindiya / mangtika": {
            "default": "Use luxury bindi/mangtika form with warm focused lighting highlighting intricate detailing.",
        },
        "ear chain kannoti": {
            "default": "Use soft intimate lighting emphasizing the chain drape and delicate ear chain design.",
        },
        "jf coin": {
            "default": "Use professional numismatic-style lighting showcasing coin detail, finish, and commemorative value.",
        },
        "watch": {
            "default": "Use watch stand or elegant display with focused professional lighting showcasing face and craftsmanship.",
            "themes": {
                "gents watch": "Use bold strong lighting emphasizing masculine design and substantial presence.",
                "ladies watch": "Use soft elegant lighting highlighting delicate details and refined aesthetic.",
            }
        },
    }

    # Try to match main category + sub-category for specific theme
    for cat_key, cat_data in backgrounds.items():
        if cat_key in category_lower or category_lower in cat_key:
            if sub_category_lower and "themes" in cat_data:
                for theme_key, theme_guidance in cat_data["themes"].items():
                    if theme_key in sub_category_lower or sub_category_lower in theme_key:
                        return theme_guidance
            # Fallback to default for this category
            return cat_data.get("default", backgrounds["bangles"]["default"])

    # Ultimate fallback
    return "Use a soft, neutral background (ivory, cream, champagne, or light marble) with warm, elegant lighting that complements the jewelry's gold tone and luxurious aesthetic."


# Large, varied headline pool. build_catalog_prompt() shuffles + samples a
# SUBSET of these into the prompt on every call so the "first example" (the
# one the model tends to just copy) is different each time — a static list
# with "Timeless Grace" always first meant every generated image echoed it.
HEADLINE_STYLE_POOL = [
    "Timeless Grace", "Pure Elegance", "Crafted Forever", "Luxury Redefined",
    "Shine Forever", "Eternal Gold", "Golden Whisper", "Radiant Heritage",
    "Woven Gold", "Quiet Luxury", "Gilded Story", "Sunlit Gold",
    "Modern Heritage", "Golden Hour", "Forever Radiant", "Bold Elegance",
    "Golden Legacy", "Graceful Gold", "Artisan Gold", "Refined Beauty",
]


def _random_headline_examples(count: int = 6) -> str:
    sample = random.sample(HEADLINE_STYLE_POOL, min(count, len(HEADLINE_STYLE_POOL)))
    return ", ".join(f'"{h}"' for h in sample)


def build_catalog_prompt(extra: str | None = None, category: str | None = None, sub_category: str | None = None) -> str:
    category_guidance = _category_background_guidance(category, sub_category)
    base_prompt = CATALOG_PROMPT_TEMPLATE.format(headline_examples=_random_headline_examples())
    if category_guidance:
        base_prompt = base_prompt.replace(
            "Use a soft beige, ivory, champagne, warm cream, or light marble luxury background.",
            f"Use a soft beige, ivory, champagne, warm cream, or light marble luxury background. {category_guidance}"
        )
    return _with_extra(base_prompt, extra)


# ── Catalog (luxury studio) prompt — verbatim from the pipeline ──────────────
CATALOG_PROMPT_TEMPLATE = """
You are a world-class luxury jewelry advertising photographer and creative director.

TASK:
Transform the uploaded jewelry product image into a premium luxury marketing advertisement.

STRICT RULES:
- Preserve the EXACT jewelry design.
- Do NOT change the shape, pattern, engraving, gemstone placement, chain style, or proportions.
- Keep the original gold color and texture.
- The jewelry must remain the hero of the image.
- Use the uploaded product image as the reference.
- Make it look like a real luxury product photoshoot.

STYLE:
Minimal, elegant, premium, luxury, high-end jewelry campaign.

BACKGROUND:
Use a soft beige, ivory, champagne, warm cream, or light marble luxury background.
Include subtle luxury props like silk fabric, marble pedestal, soft flowers,
dried baby's breath, elegant shadows, warm sunlight, premium studio lighting.
Do NOT clutter the background.

LIGHTING:
Professional luxury studio lighting. Soft diffused light. Natural gold reflections.
Premium jewelry photography. Ultra realistic.

COMPOSITION:
Center the jewelry perfectly. Keep lots of clean negative space. Balanced composition.
Magazine-quality layout.

TEXT:
Very minimal. Maximum 2-4 words. Invent a FRESH headline inspired by THIS
specific piece's look (motif, texture, mood) — do not default to the same
phrase you'd use for a different design. Style inspiration only (do not just
copy one verbatim, and don't reuse the same headline you generated last time):
{headline_examples}.
Do NOT add weight, price, purity, icons, specifications, feature lists, badges,
or unnecessary typography. Only one elegant headline.

OUTPUT:
Luxury jewelry advertisement, Instagram premium campaign, jewelry brand poster,
ultra realistic, 8K, commercial photography, luxury catalog quality, natural
shadows, soft reflections, premium color grading, high-end fashion aesthetic.

Note: Inspired by luxury campaigns from Cartier, Tiffany & Co., Bulgari,
Van Cleef & Arpels and premium Indian bridal jewelry brands. Ultra-clean
composition. Editorial luxury photography. Expensive look. Minimal typography.
Award-winning commercial product photography.
"""


# ── Describe (auto design name + website description) ────────────────────────
def build_describe_prompt(category: str, sub_category: str, weight: str, purity: str, extra: str | None = None) -> str:
    specs = []
    if category:
        specs.append(f"category: {category}")
    if sub_category:
        specs.append(f"sub-category: {sub_category}")
    if weight:
        specs.append(f"weight: {weight} g")
    if purity:
        specs.append(f"purity: {purity}")
    spec_line = "; ".join(specs) if specs else "no extra specs given"

    return (
        "You are a copywriter for a premium GOLD jewellery brand (gold only). "
        "Look at the product image and the given specs, then write for the website.\n\n"
        f"Specs — {spec_line}.\n\n"
        "Return ONLY strict JSON with two keys — BOTH are REQUIRED and must NEVER "
        "be an empty string, even with minimal specs:\n"
        '  "designName": a short, elegant, human product name (2-4 words, Title Case, '
        "no punctuation, jewellery-appropriate, e.g. 'Lotus Jhumka Set', 'Antique Choker').\n"
        '  "description": 2-3 warm sentences describing the piece for a customer '
        "(mention the look/motif/craft; you MAY mention weight/purity if given — if no "
        "specs were given, describe purely from what's visible in the image). "
        "Do NOT mention price. Do NOT invent gemstones not visible.\n\n"
        'Example: {"designName": "Temple Motif Choker", "description": "A regal '
        '22K gold choker with intricate temple motifs... "}'
        + (f"\n\nEXTRA INSTRUCTION FROM THE USER: {extra.strip()}" if (extra or "").strip() else "")
    )
