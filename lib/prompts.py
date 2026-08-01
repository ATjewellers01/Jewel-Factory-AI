"""
Prompts — ported verbatim from the proven Colab pipeline (catalog + AR position),
plus a describe prompt for auto name + description. Don't casually reword these:
the image prompts are tuned and working.

EXCEPTION: CATALOG_PROMPT_TEMPLATE's product-fidelity wording was strengthened
2026-07-31 (client-reported bleed between product colors/enamel and the
background, plus visible product-design drift after catalog generation) —
that block is intentionally NOT verbatim from the original Colab prompt.
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
            "default": "Use a wrist form or elegant stand on a silk surface with directional lighting that emphasizes curves, texture, and movement.",
            "themes": {
                "18k bangles": "Use directional lighting against a marble pedestal highlighting premium quality, intricate detailing, and luxurious 18K gold finish.",
                "antique bangle": "Use dramatic lighting on a fabric backdrop with antique props (aged wood, silk drape) emphasizing heritage aesthetic.",
                "baby bangle": "Use delicate, gentle lighting against a silk backdrop showcasing the petite, refined nature of baby bangles.",
                "fancy hmade bangle": "Use vibrant, multi-directional lighting against a fabric backdrop highlighting decorative handmade elements and ornate details.",
                "fusion bangle": "Use balanced lighting on a marble stand combining directional accents to showcase the fusion of traditional and modern designs.",
                "gajra bangle": "Use soft, romantic lighting against a silk backdrop with floral props emphasizing the bangle's floral-inspired motifs.",
                "hollow bangles": "Use directional side lighting on a wrist-form stand showcasing craftsmanship and creating elegant shadows on hollow design.",
                "indo italian bangle": "Use sophisticated lighting on a marble pedestal blending European and rich Indian aesthetics.",
                "machine bangles": "Use clean, professional lighting against a fabric backdrop emphasizing precision, symmetry, and machine-perfect craftsmanship.",
                "plaster bangle": "Use soft, even lighting against a silk backdrop that showcases the unique texture and delicate nature of plaster bangles.",
                "reli bangle": "Use layered directional lighting on a fabric backdrop emphasizing the ornate Reli patterns and detailed craftsmanship.",
                "top seller bangles": "Use showcase lighting against a marble pedestal that highlights why these are bestsellers—clear, flattering, crowd-pleasing aesthetics.",
                "v- pacheli bangle": "Use elegant, flowing directional lighting on a silk backdrop emphasizing the V-shaped Pacheli design and its graceful curves.",
            }
        },
        "earrings": {
            "default": "Use a subtle fabric backdrop (silk or velvet) with soft side lighting emphasizing details and sparkle.",
            "themes": {
                "chandbali": "Use directional lighting against a fabric backdrop highlighting the crescent moon design and ornate detailing.",
                "jhumki": "Use dramatic side lighting with elegant props showcasing jhumki's dangles and movement.",
                "kannoti earring": "Use soft intimate lighting against a silk backdrop highlighting the chain and ear chain details.",
                "tops": "Use close-up focused lighting against a velvet backdrop emphasizing stud details and gemstone work.",
                "v chain earring": "Use flowing directional lighting against a silk backdrop showcasing the V-shaped chain design and elegant drape.",
            }
        },
        "rings": {
            "default": "Use a luxury ring holder or marble pedestal with focused directional lighting showcasing band details.",
            "themes": {
                "couple ring": "Use a paired ring-holder display on a marble pedestal with matching lighting showcasing complementary designs together.",
                "gents ring": "Use bold strong lighting against a stone pedestal emphasizing masculine design and substantial presence.",
                "ladies ring": "Use soft romantic lighting against a silk backdrop with refined props enhancing femininity and delicate details.",
            }
        },
        "set": {
            "default": "Use an elegant multi-piece display stand on a silk backdrop with even lighting showcasing all pieces as cohesive collection.",
            "themes": {
                "antique set": "Use vintage props and dramatic lighting on a fabric backdrop emphasizing heritage aesthetic of entire collection.",
                "chain set": "Use a flowing layout on a silk backdrop with directional lighting emphasizing chain components and connections.",
                "choker set": "Use a mannequin-neck display or close-up intimate lighting against a plain backdrop emphasizing neckline placement and complete aesthetic.",
                "long set": "Use flowing fabric or full-length display on a silk backdrop with directional lighting showing length and drape.",
                "pendent set": "Use a necklace-form display on a marble pedestal, focused lighting emphasizing pendant as focal point while showcasing companion pieces.",
                "short set": "Use a compact focused display on a marble pedestal with lighting highlighting all pieces in unified frame.",
                "turkish set": "Use rich, ornate lighting against a fabric backdrop emphasizing the Turkish design elements and intricate craftsmanship.",
            }
        },
        "bracelet": {
            "default": "Use a bracelet stand or graceful wrist-form display on a silk backdrop with directional lighting capturing movement and texture.",
            "themes": {
                "gents bracelet / kada": "Use bold strong lighting against a stone pedestal emphasizing masculine craftsmanship and substantial design.",
                "ladies bracelet": "Use soft elegant lighting against a silk backdrop with refined props highlighting delicate details and femininity.",
            }
        },
        "pendants": {
            "default": "Use a luxury pendant stand or necklace form against a marble pedestal with focused lighting centering pendant as focal point.",
            "themes": {
                "dorla pendants": "Use directional lighting against a fabric backdrop emphasizing pendant's hanging position and ornate details.",
                "double hook pendants": "Use lighting against a marble pedestal showcasing dual-hook design and balanced aesthetic.",
                "single hook pendants": "Use focused lighting against a silk backdrop highlighting hook mechanism and main design.",
            }
        },
        "men's collection": {
            "default": "Use a bold, professional display stand on a fabric backdrop with strong masculine lighting showcasing premium craftsmanship.",
            "themes": {
                "belt buckle": "Use focused lighting against a stone pedestal emphasizing the buckle's design, texture, and masculine presence.",
                "cufflinks": "Use close-up detailed lighting against a velvet tray backdrop showcasing intricate cufflink design and precious metalwork.",
            }
        },
        "chain": {
            "default": "Use a flowing display or elegant drape on a silk backdrop with directional lighting highlighting links and craftsmanship.",
        },
        "mangalsutra": {
            "default": "Use a luxurious necklace-form display on a silk backdrop with focused intimate lighting emphasizing significance.",
        },
        "nath / nose ring": {
            "default": "Use a close-up intimate display on a velvet backdrop with soft lighting emphasizing delicate design and placement.",
        },
        "bindiya / mangtika": {
            "default": "Use a luxury bindi/mangtika form against a fabric backdrop with focused lighting highlighting intricate detailing.",
        },
        "ear chain kannoti": {
            "default": "Use soft intimate lighting against a silk backdrop emphasizing the chain drape and delicate ear chain design.",
        },
        "jf coin": {
            "default": "Use professional numismatic-style lighting on a velvet tray backdrop showcasing coin detail, finish, and commemorative value.",
        },
        "watch": {
            "default": "Use a watch stand or elegant display on a marble pedestal with focused professional lighting showcasing face and craftsmanship.",
            "themes": {
                "gents watch": "Use bold strong lighting against a stone pedestal emphasizing masculine design and substantial presence.",
                "ladies watch": "Use soft elegant lighting against a silk backdrop highlighting delicate details and refined aesthetic.",
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
    return "Use a silk or marble surface with elegant lighting that complements the jewelry's gold tone and luxurious aesthetic."


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
        anchor = (
            "gold, enamel/meenakari, or gemstone-set: always the exact same #fdf3e8 background, no matter\n"
            "what look might otherwise seem to suit the specific piece."
        )
        base_prompt = base_prompt.replace(
            anchor,
            anchor
            + "\nPROPS / SETUP for this specific category (the background COLOR stays exactly #fdf3e8 — "
            "this only changes the props, staging and lighting mood): " + category_guidance,
        )
    return _with_extra(base_prompt, extra)


# ── Catalog (luxury studio) prompt — verbatim from the pipeline ──────────────
CATALOG_PROMPT_TEMPLATE = """
You are a world-class luxury jewelry advertising photographer and creative director.

TASK:
Transform the uploaded jewelry product image into a premium luxury marketing advertisement
by changing ONLY the environment around the product — the product itself must be reproduced,
not reimagined.

STRICT RULES:
- This is the SAME physical product from the uploaded photo, not a reinterpretation or a
  similar-looking piece. Every color, enamel/meenakari pattern, engraving line, gemstone,
  and proportion must match the original pixel-for-pixel.
- Do NOT alter, smooth, simplify, stylize, or repaint the enamel/meenakari colors and
  patterns, engravings, or gemstone placement — reproduce them exactly as photographed,
  stroke for stroke and color for color.
- Do NOT change the shape, chain style, or proportions.
- Keep the original gold color and texture exactly as photographed.
- The jewelry must remain the hero of the image, completely unaltered — you are only
  changing the background/environment/lighting around it, never the product pixels.
- Make it look like a real luxury product photoshoot of THIS exact piece.

STYLE:
Minimal, elegant, premium, luxury, high-end jewelry campaign.

BACKGROUND:
MANDATORY EXACT BACKGROUND COLOR — this is not optional and applies to every single
generation, for EVERY category and sub-category of jewelry with zero exceptions:
the background base color must be the exact off-white ivory hex #fdf3e8 (RGB 253, 243, 232).
Every surface in the environment — the marble slab, the silk drape, the pedestal, the fabric
backdrop, the tray — must be that same #fdf3e8 off-white ivory. Do not shift it, do not
re-interpret it, do not "improve" it: sample the color #fdf3e8 and use it.
The only permitted deviation from #fdf3e8 is the natural light-and-shadow falloff of a real
photograph: gentle veining in the marble, soft fold-shadows in the silk, and a soft cast
shadow under the product — all of which are just slightly lighter or slightly darker
neutral shades OF #fdf3e8, never a different hue. This subtle variation is what keeps the
product's outline and every surface detail sharply distinguishable from the background at
every point along its outline, without ever making the scene look dim or tinted.
BANNED, under all circumstances, for every category: any strongly yellow, golden, honey,
caramel, amber, brown, tan, champagne, or terracotta background — a background that reads as
"sepia," "toffee-toned," or like the whole image has a yellow filter over it is a FAILURE and
must never be produced.
ALSO BANNED, equally strictly: cool grey, slate, charcoal, blue-tinted, or any background that
reads as moody/dark/overcast — that is the OPPOSITE failure and just as wrong.
ALSO BANNED: flat blown-out pure white (#ffffff) with no tonal variation at all.
The background must stay exactly #fdf3e8 — bright, clean, airy — throughout the whole frame.
Include subtle luxury props like silk fabric, a marble pedestal, soft flowers, dried baby's
breath, and soft natural shadows — all rendered in that same exact #fdf3e8 off-white ivory.
Do NOT clutter the background.
This applies to EVERY product and EVERY category/sub-category regardless of type — bangles,
earrings, rings, sets, bracelets, pendants, chains, mangalsutra, watches, everything — plain
gold, enamel/meenakari, or gemstone-set: always the exact same #fdf3e8 background, no matter
what look might otherwise seem to suit the specific piece.

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


# ── Describe (auto website description only, no design name) ────────────────────────
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
        "Return ONLY strict JSON with one key — REQUIRED and must NEVER be empty:\n"
        '  "description": 2-3 warm sentences describing the piece for a customer '
        "(mention the look/motif/craft; you MAY mention weight/purity if given — if no "
        "specs were given, describe purely from what's visible in the image). "
        "Do NOT mention price. Do NOT invent gemstones not visible.\n\n"
        'Example: {"description": "A regal 22K gold choker with intricate temple motifs... "}'
        + (f"\n\nEXTRA INSTRUCTION FROM THE USER: {extra.strip()}" if (extra or "").strip() else "")
    )
