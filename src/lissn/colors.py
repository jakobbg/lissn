"""
Color processing module for lissn.
Extracts dominant colors from show cover images using Pillow,
or deterministically generates vibrant fallback palettes from show IDs.
"""

import colorsys
import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from PIL import Image
except ImportError:
    Image = None


def hsl_to_rgb_tuple(h: float, s: float, l: float) -> Tuple[int, int, int]:
    """Convert HSL values (h: 0..360, s: 0..1, l: 0..1) to integer RGB tuple (0..255)."""
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return int(r * 255), int(g * 255), int(b * 255)


def generate_fallback_colors(show_id: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Generate a pair of complementary, vibrant RGB colors derived deterministically
    from a show ID hash string.
    """
    digest = hashlib.sha256(show_id.encode("utf-8")).hexdigest()
    hue1 = int(digest[0:4], 16) % 360
    # Secondary hue shifted by 40 to 120 degrees for contrast
    hue2 = (hue1 + 50 + (int(digest[4:8], 16) % 70)) % 360

    color1 = hsl_to_rgb_tuple(hue1, 0.70, 0.50)
    color2 = hsl_to_rgb_tuple(hue2, 0.65, 0.45)
    return color1, color2


def extract_dominant_colors(
    image_path: Path, show_id: str
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Extract primary and secondary dominant colors from an image file.
    Falls back to deterministic color generation if PIL is unavailable or image fails to load.
    """
    if Image is None or not image_path.exists():
        return generate_fallback_colors(show_id)

    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            img = img.resize((80, 80))

            # Quantize image to 16 dominant colors
            quantized = img.quantize(colors=16, method=Image.Quantize.FASTOCTREE)
            palette = quantized.getpalette()
            color_counts = quantized.getcolors()

            if not color_counts or not palette:
                return generate_fallback_colors(show_id)

            # Sort colors by frequency
            color_counts.sort(key=lambda x: x[0], reverse=True)

            extracted_colors = []
            for count, index in color_counts:
                r = palette[index * 3]
                g = palette[index * 3 + 1]
                b = palette[index * 3 + 2]

                # Filter out pure blacks/whites/grays for background gradient vibrancy
                h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
                if 0.15 < l < 0.85 and s > 0.15:
                    extracted_colors.append((r, g, b))

            if len(extracted_colors) >= 2:
                return extracted_colors[0], extracted_colors[1]
            elif len(extracted_colors) == 1:
                # Generate complementary second color
                r1, g1, b1 = extracted_colors[0]
                h, l, s = colorsys.rgb_to_hls(r1 / 255.0, g1 / 255.0, b1 / 255.0)
                color2 = hsl_to_rgb_tuple((h * 360.0 + 60.0) % 360.0, s, l)
                return extracted_colors[0], color2
    except Exception:
        pass

    return generate_fallback_colors(show_id)


def get_show_colors(cover_path: Optional[Path], show_id: str) -> Dict[str, str]:
    """
    Retrieve CSS variable declarations and color strings for a show background gradient.

    Returns:
        Dict containing color RGB strings and CSS inline style rules.
    """
    if cover_path and cover_path.exists():
        color1, color2 = extract_dominant_colors(cover_path, show_id)
    else:
        color1, color2 = generate_fallback_colors(show_id)

    r1, g1, b1 = color1
    r2, g2, b2 = color2

    return {
        "color1_rgb": f"{r1}, {g1}, {b1}",
        "color2_rgb": f"{r2}, {g2}, {b2}",
        "css_variables": f"--show-color-1-rgb: {r1}, {g1}, {b1}; --show-color-2-rgb: {r2}, {g2}, {b2};",
    }
