"""Generates static/images/og-image.png — the Open Graph / Twitter card
preview image used when the waitlist link is shared on social media.

This is a placeholder built from the same brand palette as the rest of the
site (no external assets, so it's reproducible). Swap it for a real product
screenshot or designed graphic before the real launch push by replacing
static/images/og-image.png (keep it at 1200x630).

Usage: python3 scripts/generate_og_image.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).parent.parent
OUT = ROOT / "static" / "images" / "og-image.png"

W, H = 1200, 630
SLATE_950 = (2, 6, 23)
SLATE_850 = (17, 24, 39)
SLATE_300 = (203, 213, 225)
CYAN_400 = (34, 211, 238)
WHITE = (255, 255, 255)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def build_background():
    img = Image.new("RGB", (W, H), SLATE_950)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=lerp(SLATE_950, SLATE_850, t))

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([-260, -260, 620, 560], fill=(*CYAN_400, 60))
    glow = glow.filter(ImageFilter.GaussianBlur(110))
    img.paste(glow, (0, 0), glow)

    glyphs = [("∑", 40, 60, 190), ("π", 900, 40, 150),
              ("∫", 1030, 340, 170), ("θ", 60, 420, 140)]
    glyph_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glyph_layer)
    for ch, x, y, size in glyphs:
        f = ImageFont.truetype(FONT_BOLD, size)
        gdraw.text((x, y), ch, font=f, fill=(*CYAN_400, 22))
    img.paste(glyph_layer, (0, 0), glyph_layer)
    return img


def draw_badge(draw, x, y, text):
    # Solid colors only: this draw call happens directly on the final RGBA
    # canvas, and img.convert("RGB") at save time discards alpha rather than
    # compositing it, so any alpha<255 used here would silently vanish.
    f = ImageFont.truetype(FONT_BOLD, 22)
    bbox = draw.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    dot_r = 5
    pad_left, pad_right, pad_y = 40, 24, 13
    box = [x, y, x + pad_left + tw + pad_right, y + th + pad_y * 2]
    badge_fill = (9, 35, 46)  # solid dark cyan-tinted fill, close to bg but distinct
    draw.rounded_rectangle(box, radius=999, outline=CYAN_400, width=2, fill=badge_fill)
    cy = (box[1] + box[3]) // 2
    draw.ellipse([x + 16 - dot_r, cy - dot_r, x + 16 + dot_r, cy + dot_r], fill=CYAN_400)
    draw.text((x + pad_left, y + pad_y - bbox[1]), text, font=f, fill=CYAN_400)


def main():
    img = build_background().convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Copy mirrors the actual landing page hero (badge-pill text, H1 hook,
    # and the sub-copy's "work smarter / more time with family" promise) —
    # keep this in sync if the hero copy changes again.
    draw_badge(draw, 90, 70, "AVEM UN CADOU PENTRU TINE")

    kicker_font = ImageFont.truetype(FONT_BOLD, 28)
    draw.text((90, 148), "Profa", font=kicker_font, fill=WHITE)
    profa_w = draw.textbbox((0, 0), "Profa ", font=kicker_font)[2]
    draw.text((90 + profa_w, 148), "Eficientă", font=kicker_font, fill=CYAN_400)

    title_font = ImageFont.truetype(FONT_BOLD, 76)
    draw.text((88, 195), "Ești obosit", font=title_font, fill=WHITE)
    draw.text((88, 278), "de sistem?", font=title_font, fill=CYAN_400)

    tagline_font = ImageFont.truetype(FONT_REG, 30)
    draw.text((90, 400), "Lucrează eficient. Mai mult timp cu familia", font=tagline_font, fill=SLATE_300)
    draw.text((90, 440), "și elevi pregatiti pentru examene int-un timp scurt.", font=tagline_font, fill=SLATE_300)

    cta_font = ImageFont.truetype(FONT_BOLD, 26)
    draw.text((90, 510), "Fii printre primii care află  →", font=cta_font, fill=CYAN_400)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
