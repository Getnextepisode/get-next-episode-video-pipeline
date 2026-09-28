#!/usr/bin/env python3
from __future__ import annotations
"""Render SALIIO's short branded intro/outro, with motion keyed to the sting."""
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SIZE = (1080, 1920)
FPS = 30
STINGS = {
    # These visual accents land on the four opening notes in brand sting #1.
    "intro": (2.8, "01-next-episode-intro.wav", (0.00, 0.12, 0.48, 0.79)),
    "outro": (2.5, "01-next-episode-outro.wav", (0.00, 0.24, 0.49)),
}
BRAND_COLORS = ((83, 113, 255), (143, 78, 255), (218, 92, 211), (255, 174, 132))


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def build_logo():
    source = Image.open(ROOT / "assets/brand/saliio-lockup.png").convert("RGBA")
    # Remove the nearly-black backdrop while keeping the official wordmark,
    # gradient letters, cat, and tagline intact for a clean vertical layout.
    pixels = source.load()
    for y in range(source.height):
        for x in range(source.width):
            r, g, b, _ = pixels[x, y]
            light = max(r, g, b)
            pixels[x, y] = (r, g, b, max(0, min(255, round((light - 20) * 5.2))))
    return source


def make_base():
    # A deep navy field with soft brand-colored light behind the logo.
    base = Image.new("RGB", SIZE, (4, 3, 18))
    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    draw.ellipse((100, 560, 980, 1360), fill=(92, 56, 210, 100))
    draw.ellipse((260, 700, 820, 1220), fill=(255, 166, 139, 48))
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    return Image.alpha_composite(base.convert("RGBA"), glow)


def make_brand_gradient(size):
    width, height = size
    row = Image.new("RGB", (width, 1))
    pixels = row.load()
    for x in range(width):
        position = x / max(1, width - 1) * (len(BRAND_COLORS) - 1)
        index = min(len(BRAND_COLORS) - 2, int(position))
        fraction = position - index
        left, right = BRAND_COLORS[index:index + 2]
        pixels[x, 0] = tuple(round(a + (b - a) * fraction) for a, b in zip(left, right))
    return row.resize(size, Image.Resampling.BILINEAR).convert("RGBA")


def colored_accent(gradient, mask, strength, blur):
    layer = gradient.copy()
    layer.putalpha(mask.point(lambda value: round(value * strength)))
    return layer.filter(ImageFilter.GaussianBlur(blur)) if blur else layer


def render_frames(kind: str, folder: Path, preview: Path | None = None):
    duration, _, beats = STINGS[kind]
    count = round(duration * FPS)
    logo = build_logo()
    base = make_base()
    brand_gradient = make_brand_gradient(SIZE)
    folder.mkdir(parents=True, exist_ok=True)
    preview_frame = None

    for frame in range(count):
        t = frame / FPS
        if kind == "intro":
            reveal = smooth(t / 0.32)
            scale = 0.91 + 0.09 * smooth(t / 0.85)
            fade = min(1.0, smooth(t / 0.12), smooth((duration - t) / 0.14))
        else:
            reveal = smooth(t / 0.28)
            scale = 1.0 + 0.035 * smooth(t / 0.5)
            fade = min(1.0, smooth(t / 0.12), smooth((duration - t) / 0.55))

        canvas = base.copy()
        pulse = 0.0
        for beat in beats:
            elapsed = t - beat
            if 0 <= elapsed < 0.24:
                pulse = max(pulse, (1 - elapsed / 0.24) ** 2)

        # A brand-gradient light sweep and violet halo accent the melody's
        # successive notes; the wordmark settles on the strong note at 0.79s.
        accent_mask = Image.new("L", SIZE, 0)
        accent_draw = ImageDraw.Draw(accent_mask)
        line_y = 1000 + round(90 * math.sin(min(1, t / duration) * math.pi))
        accent_draw.rounded_rectangle(
            (210, line_y, 870, line_y + 5), radius=3,
            fill=255,
        )
        accent = colored_accent(brand_gradient, accent_mask, 0.62 * pulse * fade, 12)
        canvas = Image.alpha_composite(canvas, accent)

        target_w = round(850 * scale)
        target_h = round(logo.height * target_w / logo.width)
        mark = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
        alpha = mark.getchannel("A").point(lambda value: round(value * reveal * fade))
        mark.putalpha(alpha)
        x = (SIZE[0] - target_w) // 2
        y = (SIZE[1] - target_h) // 2 - 22
        canvas.alpha_composite(mark, (x, y))

        # A compact pulse at the audio hit reinforces the actual brand colors.
        if pulse > 0.015:
            border_mask = Image.new("L", SIZE, 0)
            gd = ImageDraw.Draw(border_mask)
            inset = round(110 - pulse * 10)
            gd.rounded_rectangle(
                (inset, 610, SIZE[0] - inset, 1310), radius=58,
                outline=255, width=4,
            )
            glow = colored_accent(brand_gradient, border_mask, 0.58 * pulse * fade, 7)
            canvas = Image.alpha_composite(canvas, glow)

        path = folder / f"frame-{frame:04d}.png"
        canvas.convert("RGB").save(path, optimize=True)
        if preview and frame == round(0.95 * FPS):
            preview_frame = path

    if preview:
        preview.parent.mkdir(parents=True, exist_ok=True)
        Image.open(preview_frame or folder / "frame-0000.png").save(preview)


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in STINGS:
        raise SystemExit("usage: render_brand_sting.py intro|outro FRAME_DIR [OUTPUT_MP4]")
    kind, frame_dir = sys.argv[1], Path(sys.argv[2])
    duration, audio_name, _ = STINGS[kind]
    render_frames(kind, frame_dir)
    if len(sys.argv) < 4:
        return
    output = Path(sys.argv[3])
    audio = ROOT / "assets/brand/audio" / audio_name
    command = [
        "ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
        "-i", str(frame_dir / "frame-%04d.png"), "-i", str(audio),
        "-t", str(duration), "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-shortest", str(output),
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
