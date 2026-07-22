"""Image helpers — ported from the Colab pipeline."""
from __future__ import annotations

import io

from PIL import Image


def normalize_to_png(raw: bytes) -> bytes:
    """Re-save an uploaded image as a clean RGB PNG (avoids octet-stream/mimetype
    issues the OpenAI SDK rejects — same fix as the Colab notebook)."""
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def verify_and_center(png_bytes: bytes, canvas_size: int = 1000) -> bytes:
    """Crop to the non-transparent bounding box and re-pad into a centered square
    canvas, so pivot_x/pivot_y calibration stays consistent across AR assets.
    Does NOT change what the model generated. Raises if fully transparent."""
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")

    # Background-removal failure check: gpt-image sometimes fills the background
    # with an OPAQUE color (commonly solid black) instead of true alpha=0 — a
    # known failure mode for complex/reflective jewelry. getbbox() below only
    # looks at whether a pixel is non-zero across ALL channels, so an opaque
    # black background (0,0,0,255) is NOT excluded — the "crop" becomes a no-op
    # and the whole opaque canvas ships as a "transparent" PNG. Corners are
    # always background in these compositions, so if none of them are actually
    # transparent, background removal did not happen — fail loudly and retry
    # instead of shipping a broken (opaque-background) AR asset.
    w, h = img.size
    corners = [img.getpixel((0, 0)), img.getpixel((w - 1, 0)), img.getpixel((0, h - 1)), img.getpixel((w - 1, h - 1))]
    if all(pixel[3] > 10 for pixel in corners):
        raise ValueError("Background removal failed — image has an opaque background (not transparent). Retry generation.")

    bbox = img.getbbox()
    if bbox is None:
        raise ValueError("Image is fully transparent — generation failed, retry.")
    cropped = img.crop(bbox)

    side = max(cropped.size)
    padded = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    offset = ((side - cropped.width) // 2, (side - cropped.height) // 2)
    padded.paste(cropped, offset, cropped)

    canvas = padded.resize((canvas_size, canvas_size), Image.LANCZOS)
    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()
