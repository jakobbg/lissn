"""
Script to generate SVG, PNG, and ICO logo assets for lissn.
Creates clean vector logos, favicons, and GitHub README / app banners.
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

STATIC_DIR = Path(__file__).resolve().parent.parent / "src" / "lissn" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# 1. Standalone Icon Emblem SVG (logo-icon.svg)
SVG_ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="50%" stop-color="#1e1b4b" />
      <stop offset="100%" stop-color="#311042" />
    </linearGradient>

    <linearGradient id="ring-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="50%" stop-color="#818cf8" />
      <stop offset="100%" stop-color="#c084fc" />
    </linearGradient>

    <linearGradient id="hp-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="50%" stop-color="#a855f7" />
      <stop offset="100%" stop-color="#ec4899" />
    </linearGradient>

    <linearGradient id="bar-pink" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="#e11d48" />
      <stop offset="100%" stop-color="#fb7185" />
    </linearGradient>

    <linearGradient id="bar-purple" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="#7c3aed" />
      <stop offset="100%" stop-color="#c084fc" />
    </linearGradient>

    <linearGradient id="bar-cyan" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="#0284c7" />
      <stop offset="100%" stop-color="#38bdf8" />
    </linearGradient>

    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="10" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Background Squircle -->
  <rect x="20" y="20" width="472" height="472" rx="110" fill="url(#bg-grad)" stroke="url(#ring-grad)" stroke-width="8" />

  <!-- Headphones Arc -->
  <path d="M 126,260 A 130,130 0 0,1 386,260" fill="none" stroke="url(#hp-grad)" stroke-width="28" stroke-linecap="round" filter="url(#glow)" />

  <!-- Left Ear Cushion -->
  <rect x="98" y="235" width="38" height="85" rx="19" fill="url(#hp-grad)" />
  <rect x="106" y="243" width="22" height="69" rx="11" fill="#0f172a" opacity="0.75" />

  <!-- Right Ear Cushion -->
  <rect x="376" y="235" width="38" height="85" rx="19" fill="url(#hp-grad)" />
  <rect x="384" y="243" width="22" height="69" rx="11" fill="#0f172a" opacity="0.75" />

  <!-- Equalizer Waves & L-Shape -->
  <rect x="176" y="190" width="26" height="140" rx="13" fill="url(#bar-pink)" />
  <rect x="176" y="304" width="76" height="26" rx="13" fill="url(#bar-pink)" />

  <rect x="222" y="235" width="22" height="55" rx="11" fill="url(#bar-purple)" />
  <rect x="260" y="170" width="24" height="120" rx="12" fill="url(#bar-cyan)" />
  <rect x="298" y="215" width="22" height="75" rx="11" fill="url(#bar-purple)" />
  <rect x="334" y="245" width="20" height="45" rx="10" fill="url(#bar-pink)" opacity="0.95" />

  <!-- Pulse Dot -->
  <circle cx="272" cy="317" r="9" fill="#38bdf8" />
</svg>"""

# 2. Favicon SVG (clean transparent-bg icon badge for browser tab)
SVG_FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="100%" height="100%">
  <defs>
    <linearGradient id="fav-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#1e1b4b" />
    </linearGradient>
    <linearGradient id="fav-hp" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="50%" stop-color="#818cf8" />
      <stop offset="100%" stop-color="#c084fc" />
    </linearGradient>
    <linearGradient id="fav-accent" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="#f43f5e" />
      <stop offset="100%" stop-color="#fb7185" />
    </linearGradient>
  </defs>

  <rect width="64" height="64" rx="16" fill="url(#fav-bg)" />
  <path d="M 16,33 A 16,16 0 0,1 48,33" fill="none" stroke="url(#fav-hp)" stroke-width="4.5" stroke-linecap="round" />

  <rect x="12" y="30" width="5.5" height="12" rx="2.75" fill="url(#fav-hp)" />
  <rect x="46.5" y="30" width="5.5" height="12" rx="2.75" fill="url(#fav-hp)" />

  <!-- Stylized L & Sound bars -->
  <rect x="22" y="24" width="4" height="18" rx="2" fill="url(#fav-accent)" />
  <rect x="22" y="38" width="10" height="4" rx="2" fill="url(#fav-accent)" />

  <rect x="28" y="29" width="3.5" height="8" rx="1.75" fill="#818cf8" />
  <rect x="33" y="21" width="4" height="16" rx="2" fill="#38bdf8" />
  <rect x="39" y="27" width="3.5" height="10" rx="1.75" fill="#c084fc" />
</svg>"""

# 3. Horizontal Banner SVG (logo-banner.svg)
SVG_BANNER = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 220" width="100%" height="100%">
  <defs>
    <linearGradient id="b-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0f1d" />
      <stop offset="50%" stop-color="#111827" />
      <stop offset="100%" stop-color="#1e1b4b" />
    </linearGradient>

    <linearGradient id="b-border" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.8" />
      <stop offset="50%" stop-color="#818cf8" stop-opacity="0.8" />
      <stop offset="100%" stop-color="#c084fc" stop-opacity="0.8" />
    </linearGradient>

    <linearGradient id="b-hp" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="50%" stop-color="#818cf8" />
      <stop offset="100%" stop-color="#c084fc" />
    </linearGradient>

    <linearGradient id="b-pink" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="#e11d48" />
      <stop offset="100%" stop-color="#fb7185" />
    </linearGradient>

    <linearGradient id="b-cyan" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="#0284c7" />
      <stop offset="100%" stop-color="#38bdf8" />
    </linearGradient>

    <linearGradient id="b-purple" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="#7c3aed" />
      <stop offset="100%" stop-color="#c084fc" />
    </linearGradient>

    <linearGradient id="b-text-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ffffff" />
      <stop offset="60%" stop-color="#f1f5f9" />
      <stop offset="100%" stop-color="#cbd5e1" />
    </linearGradient>

    <linearGradient id="b-subtext-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="50%" stop-color="#818cf8" />
      <stop offset="100%" stop-color="#c084fc" />
    </linearGradient>

    <filter id="b-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Banner Outer Frame -->
  <rect x="8" y="8" width="784" height="204" rx="28" fill="url(#b-bg)" stroke="url(#b-border)" stroke-width="2" />

  <!-- EMBLEM ICON (Left side offset X: 45, Y: 30, Scale: ~0.7) -->
  <g transform="translate(45, 30)">
    <!-- Background Circle -->
    <rect x="0" y="0" width="160" height="160" rx="40" fill="#0f172a" stroke="url(#b-hp)" stroke-width="3" />

    <!-- Headphones Arc -->
    <path d="M 40,82 A 42,42 0 0,1 120,82" fill="none" stroke="url(#b-hp)" stroke-width="10" stroke-linecap="round" filter="url(#b-glow)" />

    <!-- Left Ear Cushion -->
    <rect x="31" y="74" width="13" height="28" rx="6.5" fill="url(#b-hp)" />
    <rect x="34" y="77" width="7" height="22" rx="3.5" fill="#0f172a" opacity="0.8" />

    <!-- Right Ear Cushion -->
    <rect x="116" y="74" width="13" height="28" rx="6.5" fill="url(#b-hp)" />
    <rect x="119" y="77" width="7" height="22" rx="3.5" fill="#0f172a" opacity="0.8" />

    <!-- Sound Equalizer L-Shape -->
    <rect x="56" y="58" width="9" height="46" rx="4.5" fill="url(#b-pink)" />
    <rect x="56" y="95" width="25" height="9" rx="4.5" fill="url(#b-pink)" />

    <rect x="71" y="73" width="7" height="18" rx="3.5" fill="url(#b-purple)" />
    <rect x="83" y="52" width="8" height="39" rx="4" fill="url(#b-cyan)" />
    <rect x="96" y="67" width="7" height="24" rx="3.5" fill="url(#b-purple)" />
    <rect x="107" y="76" width="6" height="15" rx="3" fill="url(#b-pink)" opacity="0.9" />

    <circle cx="87" cy="100" r="3" fill="#38bdf8" />
  </g>

  <!-- BRAND WORDMARK "lissn" -->
  <text x="240" y="122" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="88" font-weight="900" letter-spacing="-3" fill="url(#b-text-grad)">lissn</text>

  <!-- Glowing Sound Wave Accent behind dot on 'i' -->
  <circle cx="360" cy="58" r="8" fill="#38bdf8" filter="url(#b-glow)" />

  <!-- TAGLINE SUBTEXT -->
  <text x="245" y="160" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="20" font-weight="700" letter-spacing="4" fill="url(#b-subtext-grad)">AUDIOBOOKS &amp; PODCASTS</text>

  <!-- Right Side Decorative Audio Waves -->
  <g transform="translate(680, 75)" opacity="0.85">
    <rect x="0" y="20" width="5" height="30" rx="2.5" fill="#38bdf8" />
    <rect x="12" y="10" width="5" height="50" rx="2.5" fill="#818cf8" />
    <rect x="24" y="0" width="5" height="70" rx="2.5" fill="#c084fc" />
    <rect x="36" y="15" width="5" height="40" rx="2.5" fill="#f43f5e" />
    <rect x="48" y="25" width="5" height="20" rx="2.5" fill="#38bdf8" />
  </g>
</svg>"""

def render_pillow_favicon(size=64):
    """Draw a clean, pixel-perfect raster icon using Pillow for PNG & ICO generation."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background
    padding = max(1, size // 32)
    radius = size // 4
    
    # Background color #0f172a
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=radius,
        fill=(15, 23, 42, 255),
        outline=(56, 189, 248, 255),
        width=max(1, size // 32)
    )

    # Headphones arc
    arc_box = [size * 0.22, size * 0.22, size * 0.78, size * 0.78]
    draw.arc(arc_box, start=180, end=360, fill=(129, 140, 248, 255), width=max(2, size // 14))

    # Ear cushions
    c_w = size // 10
    c_h = size // 4
    draw.rounded_rectangle([size * 0.18, size * 0.45, size * 0.18 + c_w, size * 0.45 + c_h], radius=c_w//2, fill=(56, 189, 248, 255))
    draw.rounded_rectangle([size * 0.82 - c_w, size * 0.45, size * 0.82, size * 0.45 + c_h], radius=c_w//2, fill=(192, 132, 252, 255))

    # Equalizer bars
    # L-Stem
    l_x = size * 0.35
    l_w = max(2, size // 16)
    draw.rounded_rectangle([l_x, size * 0.38, l_x + l_w, size * 0.68], radius=l_w//2, fill=(244, 63, 94, 255))
    draw.rounded_rectangle([l_x, size * 0.62, l_x + size * 0.16, size * 0.62 + l_w], radius=l_w//2, fill=(244, 63, 94, 255))

    # Bars
    draw.rounded_rectangle([size * 0.46, size * 0.48, size * 0.46 + l_w, size * 0.60], radius=l_w//2, fill=(129, 140, 248, 255))
    draw.rounded_rectangle([size * 0.54, size * 0.34, size * 0.54 + l_w, size * 0.60], radius=l_w//2, fill=(56, 189, 248, 255))
    draw.rounded_rectangle([size * 0.62, size * 0.44, size * 0.62 + l_w, size * 0.60], radius=l_w//2, fill=(192, 132, 252, 255))

    return img


def generate_all():
    print("Generating SVG vector logo files...")
    (STATIC_DIR / "logo-icon.svg").write_text(SVG_ICON, encoding="utf-8")
    (STATIC_DIR / "logo.svg").write_text(SVG_ICON, encoding="utf-8")
    (STATIC_DIR / "favicon.svg").write_text(SVG_FAVICON, encoding="utf-8")
    (STATIC_DIR / "logo-banner.svg").write_text(SVG_BANNER, encoding="utf-8")

    print("Generating PNG and ICO favicons via Pillow...")
    img_16 = render_pillow_favicon(16)
    img_32 = render_pillow_favicon(32)
    img_48 = render_pillow_favicon(48)
    img_180 = render_pillow_favicon(180)
    img_512 = render_pillow_favicon(512)

    img_32.save(STATIC_DIR / "favicon-32x32.png", format="PNG")
    img_180.save(STATIC_DIR / "apple-touch-icon.png", format="PNG")
    img_512.save(STATIC_DIR / "android-chrome-512x512.png", format="PNG")

    # Multi-size ICO file containing 16x16, 32x32, 48x48
    img_32.save(
        STATIC_DIR / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[img_16, img_48]
    )

    print("Logo asset generation complete!")

if __name__ == "__main__":
    generate_all()
