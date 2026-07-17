"""
Prompts — ported verbatim from the proven Colab pipeline (catalog + AR position),
plus a describe prompt for auto name + description. Don't casually reword these:
the image prompts are tuned and working.
"""

# ── AR / transparent try-on positioning (per jewellery type) ─────────────────
POSITION_INSTRUCTIONS = {
    "necklace": (
        "Remove the Background"
        "Show the necklace laid flat, photographed from directly the front "
        "(straight-on, not tilted), as if worn facing the viewer. "
        "Position it top-center of the frame with the clasp/chain top edge "
        "touching the top boundary. Center it horizontally."
    ),
    "earring_left": (
        "Remove the Background"
        "Show a single earring photographed straight-on from the front. "
        "Position it in the right-center of the frame (since this earring "
        "will render on the wearer's left ear, camera-left = wearer's right "
        "in a mirrored view). Hook or post should point upward, top of frame."
    ),
    "earring_right": (
        "Remove the Background"
        "Show a single earring photographed straight-on from the front. "
        "Position it in the left-center of the frame. Hook or post should "
        "point upward, top of frame."
    ),
    "ring_index": (
        "Remove the Background"
        "Show the ring photographed from directly above/front, band facing "
        "the viewer, centered exactly in the middle of the frame, "
        "front-facing top-down view as if worn on an index finger."
    ),
    "ring_middle": (
        "Remove the Background"
        "Show the ring photographed from directly above/front, band facing "
        "the viewer, centered exactly in the middle of the frame."
    ),
    "bangle": (
        "Remove the Background"
        "Show the bangle photographed straight-on from the front, as a "
        "flat circular/oval shape, centered exactly in the middle of the "
        "frame, as if worn on a wrist facing the viewer."
    ),
}

AR_BASE_INSTRUCTION = (
    "Do not redesign, resize, or alter the jewellery's shape, gemstones, "
    "engravings, or proportions — preserve the exact product exactly as "
    "photographed. Only remove the background completely, leaving 100% "
    "transparent pixels (alpha=0) around the product. No shadow, no "
    "reflection, no watermark, no border. The product must fill "
    "70-85% of the frame with even padding on all sides."
)


def _with_extra(prompt: str, extra: str | None) -> str:
    """Append the manufacturer's regenerate instruction, if any."""
    extra = (extra or "").strip()
    if not extra:
        return prompt
    return f"{prompt}\n\nADDITIONAL INSTRUCTION FROM THE USER (follow it while keeping the product exact): {extra}"


def build_ar_prompt(jtype: str, extra: str | None = None) -> str:
    pos = POSITION_INSTRUCTIONS.get(jtype, POSITION_INSTRUCTIONS["necklace"])
    return _with_extra(f"{pos} {AR_BASE_INSTRUCTION}", extra)


def build_catalog_prompt(extra: str | None = None) -> str:
    return _with_extra(CATALOG_PROMPT, extra)


# ── Catalog (luxury studio) prompt — verbatim from the pipeline ──────────────
CATALOG_PROMPT = """
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
Very minimal. Maximum 2-4 words. Examples: "Timeless Grace", "Pure Elegance",
"Crafted Forever", "Luxury Redefined", "Shine Forever", "Eternal Gold".
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
        "Return ONLY strict JSON with two keys:\n"
        '  "designName": a short, elegant, human product name (2-4 words, Title Case, '
        "no punctuation, jewellery-appropriate, e.g. 'Lotus Jhumka Set', 'Antique Choker').\n"
        '  "description": 2-3 warm sentences describing the piece for a customer '
        "(mention the look/motif/craft; you MAY mention weight/purity if given). "
        "Do NOT mention price. Do NOT invent gemstones not visible.\n\n"
        'Example: {"designName": "Temple Motif Choker", "description": "A regal '
        '22K gold choker with intricate temple motifs... "}'
        + (f"\n\nEXTRA INSTRUCTION FROM THE USER: {extra.strip()}" if (extra or "").strip() else "")
    )
