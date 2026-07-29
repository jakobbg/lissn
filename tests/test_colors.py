"""
Tests for lissn.colors module.
Verifies color extraction, fallback palette generation, and CSS variables.
"""

from pathlib import Path
from PIL import Image

from lissn.colors import (
    extract_dominant_colors,
    generate_fallback_colors,
    get_show_colors,
    hsl_to_rgb_tuple,
)


def test_generate_fallback_colors():
    """Test deterministic fallback color generation from show_id."""
    color1, color2, color3 = generate_fallback_colors("test_show_123")
    assert len(color1) == 3
    assert len(color2) == 3
    assert len(color3) == 3
    assert all(0 <= c <= 255 for c in color1)
    assert all(0 <= c <= 255 for c in color2)
    assert all(0 <= c <= 255 for c in color3)

    # Verify deterministic output
    color1_again, color2_again, color3_again = generate_fallback_colors("test_show_123")
    assert color1 == color1_again
    assert color2 == color2_again
    assert color3 == color3_again


def test_hsl_to_rgb_tuple():
    """Test HSL to RGB conversion."""
    r, g, b = hsl_to_rgb_tuple(0, 1.0, 0.5)  # Pure red
    assert (r, g, b) == (255, 0, 0)


def test_extract_dominant_colors(tmp_path: Path):
    """Test extracting dominant colors from a sample cover image."""
    img_path = tmp_path / "test_cover.png"
    # Create a test 100x100 image with two distinct color halves (blue & orange)
    img = Image.new("RGB", (100, 100), (30, 144, 255))
    for x in range(50, 100):
        for y in range(100):
            img.putpixel((x, y), (255, 140, 0))
    img.save(img_path)

    color1, color2, color3 = extract_dominant_colors(img_path, "test_show")
    assert len(color1) == 3
    assert len(color2) == 3
    assert len(color3) == 3


def test_extract_dominant_colors_invalid_image(tmp_path: Path):
    """Test fallback to deterministic palette when encountering a broken/corrupted image file."""
    corrupted_img = tmp_path / "corrupted.jpg"
    corrupted_img.write_bytes(b"not an image file")

    c1, c2, c3 = extract_dominant_colors(corrupted_img, "show_fallback_123")
    expected_c1, expected_c2, expected_c3 = generate_fallback_colors("show_fallback_123")

    assert c1 == expected_c1
    assert c2 == expected_c2
    assert c3 == expected_c3


def test_get_show_colors(tmp_path: Path):
    """Test get_show_colors formatting for template rendering."""
    res_no_cover = get_show_colors(None, "show_abc")
    assert "color1_rgb" in res_no_cover
    assert "color2_rgb" in res_no_cover
    assert "color3_rgb" in res_no_cover
    assert "css_variables" in res_no_cover
    assert "--show-color-1-rgb:" in res_no_cover["css_variables"]
    assert "--show-color-2-rgb:" in res_no_cover["css_variables"]
    assert "--show-color-3-rgb:" in res_no_cover["css_variables"]

    # Test with cover image
    img_path = tmp_path / "cover.jpg"
    img = Image.new("RGB", (50, 50), (120, 50, 200))
    img.save(img_path)

    res_with_cover = get_show_colors(img_path, "show_abc")
    assert "--show-color-1-rgb:" in res_with_cover["css_variables"]
