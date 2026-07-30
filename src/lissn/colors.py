"""
Color processing module for lissn.
Extracts dominant base and accent colors from show cover images using Pillow,
or deterministically generates vibrant fallback palettes from show IDs.
"""

import colorsys
import hashlib
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import io

try:
    from PIL import Image
except ImportError:
    Image = None


def hsl_to_rgb_tuple(h: float, s: float, l: float) -> Tuple[int, int, int]:
    """Convert HSL values (h: 0..360, s: 0..1, l: 0..1) to integer RGB tuple (0..255)."""
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return int(r * 255), int(g * 255), int(b * 255)


def color_distance(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> float:
    """Calculate Euclidean distance between two RGB color tuples."""
    return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2)


def generate_fallback_colors(
    show_id: str,
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Generate a set of 3 complementary, vibrant RGB colors derived deterministically
    from a show ID hash string.
    """
    digest = hashlib.sha256(show_id.encode("utf-8")).hexdigest()
    hue1 = int(digest[0:4], 16) % 360
    hue2 = (hue1 + 45 + (int(digest[4:8], 16) % 60)) % 360
    hue3 = (hue1 + 160 + (int(digest[8:12], 16) % 80)) % 360

    color1 = hsl_to_rgb_tuple(hue1, 0.75, 0.48)
    color2 = hsl_to_rgb_tuple(hue2, 0.70, 0.42)
    color3 = hsl_to_rgb_tuple(hue3, 0.80, 0.55)
    return color1, color2, color3


def extract_dominant_colors(
    image_source: Optional[Union[Path, bytes]], show_id: str
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Extract primary base, secondary base, and accent colors from an image cover file or raw binary bytes.
    Falls back to deterministic color generation if PIL is unavailable or image fails to load.
    """
    if Image is None or image_source is None:
        return generate_fallback_colors(show_id)

    try:
        if isinstance(image_source, bytes):
            img_obj = Image.open(io.BytesIO(image_source))
        elif isinstance(image_source, Path) and image_source.exists():
            img_obj = Image.open(image_source)
        else:
            return generate_fallback_colors(show_id)

        with img_obj as img:
            img = img.convert("RGB")
            img = img.resize((100, 100))

            # Quantize image to 32 dominant colors
            quantized = img.quantize(colors=32, method=Image.Quantize.FASTOCTREE)
            palette = quantized.getpalette()
            color_counts = quantized.getcolors()

            if not color_counts or not palette:
                return generate_fallback_colors(show_id)

            # Sort palette colors by pixel frequency
            color_counts.sort(key=lambda x: x[0], reverse=True)

            raw_colors: List[Tuple[int, int, int]] = []
            for count, index in color_counts:
                r = palette[index * 3]
                g = palette[index * 3 + 1]
                b = palette[index * 3 + 2]
                raw_colors.append((r, g, b))

            if not raw_colors:
                return generate_fallback_colors(show_id)

            # 1. Primary Base Color: top color that isn't extreme pure white or black if possible
            primary = raw_colors[0]
            for c in raw_colors:
                h, l, s = colorsys.rgb_to_hls(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)
                if 0.08 < l < 0.92:
                    primary = c
                    break

            # 2. Secondary Base Color: distinct from primary (Euclidean distance > 45)
            secondary = None
            for c in raw_colors:
                if color_distance(primary, c) > 45:
                    secondary = c
                    break

            if secondary is None:
                pr, pg, pb = primary
                h, l, s = colorsys.rgb_to_hls(pr / 255.0, pg / 255.0, pb / 255.0)
                secondary = hsl_to_rgb_tuple((h * 360.0 + 50.0) % 360.0, s, l)

            # 3. Accent Color: highest saturation in the image palette
            accent = None
            best_sat = -1.0
            for c in raw_colors:
                h, l, s = colorsys.rgb_to_hls(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)
                if s > best_sat and color_distance(primary, c) > 30:
                    best_sat = s
                    accent = c

            if accent is None:
                sr, sg, sb = secondary
                h, l, s = colorsys.rgb_to_hls(sr / 255.0, sg / 255.0, sb / 255.0)
                accent = hsl_to_rgb_tuple((h * 360.0 + 120.0) % 360.0, max(s, 0.6), l)

            return primary, secondary, accent
    except Exception:
        pass

    return generate_fallback_colors(show_id)


def get_show_colors(image_source: Optional[Union[Path, bytes]], show_id: str) -> Dict[str, str]:
    """
    Retrieve CSS variable declarations and color strings for a show background gradient.

    Returns:
        Dict containing color RGB strings and CSS inline style rules.
    """
    if image_source:
        color1, color2, color3 = extract_dominant_colors(image_source, show_id)
    else:
        color1, color2, color3 = generate_fallback_colors(show_id)

    r1, g1, b1 = color1
    r2, g2, b2 = color2
    r3, g3, b3 = color3

    css_vars = (
        f"--show-color-1-rgb: {r1}, {g1}, {b1}; "
        f"--show-color-2-rgb: {r2}, {g2}, {b2}; "
        f"--show-color-3-rgb: {r3}, {g3}, {b3};"
    )

    return {
        "color1_rgb": f"{r1}, {g1}, {b1}",
        "color2_rgb": f"{r2}, {g2}, {b2}",
        "color3_rgb": f"{r3}, {g3}, {b3}",
        "css_variables": css_vars,
    }
