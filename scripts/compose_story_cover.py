#!/usr/bin/env python3
"""Compose the fixed, story-specific vertical cover with real, shaped typography."""
import json
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, features

W, H = 1080, 1920
RAQM = features.check_feature("raqm")


def pick_font(bold=False):
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansHebrew-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for item in candidates:
        if Path(item).exists():
            return item
    raise RuntimeError("No compatible Hebrew font is installed")


FONT = pick_font(True)
DRAW = None


def clean(value):
    value = str(value or "")
    value = re.sub(r"[^\w\s\u0590-\u05ff.,!?׳״’'־:—–()\-]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def story_teaser(manifest, title):
    # The promo endpoint currently returns a precomposed teaser. Remove its
    # repeated title and marketing footer so the cover carries only the hook.
    teaser = clean(manifest.get("tagline") or manifest.get("hook") or manifest.get("teaser") or "")
    if title:
        teaser = re.sub(r"^" + re.escape(clean(title)) + r"[.!?\s–—-]*", "", teaser, flags=re.I).strip()
    teaser = re.sub(r"\s*הפרק הראשון מחכה עכשיו ב[־-]?SALIIO\.?\s*$", "", teaser, flags=re.I).strip()
    teaser = re.sub(r"\s*המשך הסיפור מחכה ב.*$", "", teaser, flags=re.I).strip()
    teaser = teaser or clean(manifest.get("teaser") or "סיפור חדש מחכה לכם בפרק הראשון.")
    # Keep the cover on the hook. Long promo blurbs often contain the reveal;
    # never let a full synopsis spill onto the poster.
    if len(teaser) > 118:
        shortened = teaser[:118].rsplit(" ", 1)[0].rstrip(".,:;־- ")
        teaser = shortened + "…"
    return teaser


def font(size):
    return ImageFont.truetype(FONT, size)


def direction(is_rtl):
    return "rtl" if is_rtl and RAQM else "ltr"


def measure(value, face, is_rtl):
    options = {"direction": direction(is_rtl)} if RAQM else {}
    return DRAW.textlength(value, font=face, **options)


def wrap(text, face, width, is_rtl):
    lines = []
    for para in str(text).split("\n"):
        line = ""
        for word in para.split():
            candidate = (line + " " + word).strip()
            if line and measure(candidate, face, is_rtl) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
    return lines


def draw_fit(text, box, max_size, min_size, color, *, rtl=True, bold=True, spacing=1.28, align="center"):
    x, y, width, height = box
    global FONT
    old_font = FONT
    FONT = pick_font(bold)
    chosen = None
    lines = []
    step = 0
    for size in range(max_size, min_size - 1, -2):
        face = font(size)
        candidate = wrap(text, face, width, rtl)
        line_step = int(size * spacing)
        if len(candidate) * line_step <= height and all(measure(line, face, rtl) <= width for line in candidate):
            chosen, lines, step = face, candidate, line_step
            break
    if chosen is None:
        FONT = old_font
        raise ValueError(f"Text does not fit its cover region: {text[:80]}")
    for index, line in enumerate(lines):
        # Local macOS preview does not ship RAQM; reversing only for that
        # preview keeps its visual direction. GitHub Actions uses RAQM shaping.
        rendered = line if RAQM or not rtl else line[::-1]
        anchor = "mt" if align == "center" else ("rt" if rtl else "lt")
        px = x + width / 2 if align == "center" else (x + width if rtl else x)
        options = {"direction": direction(rtl)} if RAQM else {}
        DRAW.text((px, y + index * step), rendered, font=chosen, fill=color,
                  anchor=anchor, stroke_width=1, stroke_fill=(0, 0, 0, 180), **options)
    FONT = old_font
    return len(lines) * step


def centered_latin(text, center, top, size, color, bold=True):
    global FONT
    old = FONT
    FONT = pick_font(bold)
    face = font(size)
    options = {"direction": "ltr"} if RAQM else {}
    DRAW.text((center, top), text, font=face, fill=color, anchor="mt", **options)
    FONT = old


def rounded_card(draw, box, radius=34, fill=(8, 12, 19, 215), outline=(255, 255, 255, 50), width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def icon_book(draw, cx, cy, scale=1):
    c = (255, 255, 255, 245)
    s = scale
    draw.line([(cx,cy-18*s),(cx-3*s,cy-12*s),(cx-3*s,cy+18*s)], fill=c, width=max(2,int(3*s)))
    draw.line([(cx-4*s,cy-12*s),(cx-18*s,cy-17*s),(cx-23*s,cy-15*s),(cx-23*s,cy+13*s),(cx-5*s,cy+18*s)], fill=c, width=max(2,int(3*s)), joint="curve")
    draw.line([(cx+3*s,cy-12*s),(cx+18*s,cy-17*s),(cx+23*s,cy-15*s),(cx+23*s,cy+13*s),(cx+4*s,cy+18*s)], fill=c, width=max(2,int(3*s)), joint="curve")


def icon_headphones(draw, cx, cy, scale=1):
    c = (255,255,255,245); s=scale
    draw.arc((cx-22*s,cy-23*s,cx+22*s,cy+21*s),180,360,fill=c,width=max(2,int(3*s)))
    draw.rounded_rectangle((cx-23*s,cy-3*s,cx-14*s,cy+17*s),radius=4*s,fill=c)
    draw.rounded_rectangle((cx+14*s,cy-3*s,cx+23*s,cy+17*s),radius=4*s,fill=c)


def icon_chat(draw, cx, cy, scale=1):
    c=(255,255,255,245); s=scale
    draw.rounded_rectangle((cx-23*s,cy-17*s,cx+23*s,cy+12*s),radius=9*s,outline=c,width=max(2,int(3*s)))
    draw.line([(cx-10*s,cy+12*s),(cx-17*s,cy+21*s),(cx+1*s,cy+12*s)],fill=c,width=max(2,int(3*s)),joint="curve")


def icon_star(draw, cx, cy, radius=21, color="#ffc84a"):
    points=[]
    for i in range(10):
        angle=-math.pi/2+i*math.pi/5
        r=radius if i%2==0 else radius*.45
        points.append((cx+math.cos(angle)*r,cy+math.sin(angle)*r))
    draw.polygon(points,fill=color)


def metric_value(manifest, *keys):
    for key in keys:
        val = manifest.get(key)
        if val is not None and str(val).strip() and str(val).strip().lower() not in ("0", "none", "null"):
            return str(val).strip()
    return None


def main():
    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    base = ImageOps.fit(Image.open(sys.argv[2]).convert("RGB"), (W,H), method=Image.Resampling.LANCZOS).convert("RGBA")
    # Gentle cinematic scrim: preserve the generated location while protecting legibility.
    shade = Image.new("RGBA", (W,H))
    pixels = shade.load()
    for y in range(H):
        center = abs((y - H * .50) / (H * .50))
        alpha = int(38 + 108 * center)
        for x in range(W):
            pixels[x,y] = (3,5,10,alpha)
    base = Image.alpha_composite(base, shade)
    global DRAW
    DRAW = ImageDraw.Draw(base)

    logo = Image.open(sys.argv[3]).convert("RGBA")
    logo.thumbnail((142,142), Image.Resampling.LANCZOS)
    base.alpha_composite(logo, (68,72))
    centered_latin("GET NEXT", 405, 91, 54, "#ffffff")
    centered_latin("EPISODE", 755, 91, 54, "#ff1838")
    centered_latin("READ  •  LISTEN  •  CHAT STORIES", 574, 157, 25, "#f1f2f5", False)
    DRAW.line((72,252,1008,252), fill=(255,255,255,70), width=2)

    title = clean(manifest.get("title") or "סיפור חדש")
    genre = clean(manifest.get("genre") or manifest.get("category") or "סיפור מקורי")
    teaser = story_teaser(manifest, title)
    draw_fit(genre, (80,310,920,72), 42, 30, "#ff3049")
    draw_fit(title, (62,394,956,285), 142, 64, "#fffaf4", spacing=1.08)

    # A fine red rule anchors the title block without turning copy into subtitles.
    DRAW.rounded_rectangle((440,694,640,702), radius=4, fill="#ff1838")
    draw_fit(teaser, (110,740,860,245), 55, 34, "#ffffff", spacing=1.25)

    # Clear product promise using a consistent, hand-drawn icon set.
    rounded_card(DRAW, (86,1060,994,1292), radius=38, fill=(6,10,17,205), outline=(255,255,255,68), width=2)
    labels = [(250,"קריאה",icon_book),(540,"האזנה",icon_headphones),(830,"צ׳אט",icon_chat)]
    for cx, label, icon in labels:
        icon(DRAW, cx, 1130, 1.15)
        DRAW.rounded_rectangle((cx-3,1172,cx+3,1182),radius=3,fill="#ff1838")
        draw_fit(label, (cx-108,1194,216,58), 36, 28, "#ffffff")

    rating = metric_value(manifest,"rating","averageRating")
    readers = metric_value(manifest,"readers","readerCount")
    if rating and readers:
        icon_star(DRAW,360,1403,22)
        draw_fit(rating + " / 5", (398,1367,180,70), 42, 34, "#ffc84a", rtl=False)
        DRAW.ellipse((558,1392,572,1406),fill="#ff1838")
        centered_latin(readers, 670, 1372, 42, "#ffffff")
        draw_fit("קוראים", (745,1367,175,70), 42, 32, "#ffffff")
    elif rating:
        icon_star(DRAW,470,1403,22)
        draw_fit(rating + " / 5", (510,1367,180,70), 42, 34, "#ffc84a", rtl=False)
    elif readers:
        centered_latin(readers, 495, 1372, 42, "#ffffff")
        draw_fit("קוראים", (550,1367,175,70), 42, 32, "#ffffff")

    rounded_card(DRAW, (92,1512,988,1660), radius=42, fill="#e50924", outline=(255,104,116,255), width=3)
    draw_fit("הפרק הראשון מחכה לך", (130,1545,812,80), 50, 36, "#ffffff")
    DRAW.line([(915,1572),(935,1586),(915,1600)], fill="#ffffff", width=7, joint="curve")
    centered_latin("@GetNextEpisodeBot", 540, 1701, 44, "#ff3049")
    base.convert("RGB").save(sys.argv[4], quality=96)


if __name__ == "__main__":
    main()
