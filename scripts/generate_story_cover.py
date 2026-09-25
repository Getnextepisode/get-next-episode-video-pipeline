#!/usr/bin/env python3
import base64
import json
import os
import sys
import urllib.error
import urllib.request

manifest_path = sys.argv[1] if len(sys.argv) > 1 else "build/manifest.json"
output_path = sys.argv[2] if len(sys.argv) > 2 else "build/ai-cover.png"
api_key = os.environ.get("OPENAI_API_KEY", "").strip()
if not api_key:
    print("OPENAI_API_KEY is unavailable; keeping the existing cover.")
    raise SystemExit(2)

with open(manifest_path, encoding="utf-8") as handle:
    story = json.load(handle)

title = str(story.get("title") or "Get Next Episode").strip()
genre = str(story.get("genre") or story.get("category") or "Original story").strip()
teaser = str(story.get("teaser") or "").strip()
rating = str(story.get("rating") or "4.8")
readers = str(story.get("readers") or story.get("views") or "18.4K")

prompt = f"""
Create a premium cinematic vertical 9:16 promotional book-cover image for a serialized chat story.
Match this art direction: high-end streaming thriller poster, deep black shadows, warm practical light,
red white and black palette, dramatic realistic photography, sharp typography, polished advertising finish.

Story:
- Exact title: {title}
- Genre: {genre}
- Description: {teaser}
- Rating: {rating}
- Readers: {readers}

Composition:
- Reserve the top 18 percent as a clean dark header. Do not place a logo or brand name there.
- Put the genre in small distressed red type.
- Put the exact story title very large in bold white distressed type.
- Under it place this exact Hebrew promise on two lines:
  סיפורים שנקראים כמו צ׳אט.
  נשמעים כמו סדרה.
- Include one premium voice-message bubble with a red play button and waveform.
- Include two realistic dark chat bubbles that visually communicate a live conversation.
- Show the rating and readers in a clear gold and white line.
- Near the bottom add a polished red CTA with this exact Hebrew text:
  לקרוא או להאזין לפרק הראשון
- At the bottom add exactly: @GetNextEpisodeBot
- Keep every element inside mobile-safe margins.
- No subtitles, no captions, no extra logos, no yellow buttons, no gibberish, no invented symbols.
- The image must look like a finished professional cover, not a UI mockup.
"""

payload = json.dumps({
    "model": "gpt-image-1",
    "size": "1024x1536",
    "quality": "high",
    "response_format": "b64_json",
    "prompt": prompt,
}).encode("utf-8")
request = urllib.request.Request(
    "https://api.openai.com/v1/images/generations",
    data=payload,
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.load(response)
except urllib.error.HTTPError as error:
    detail = error.read().decode("utf-8", "replace")
    print(f"Image generation failed ({error.code}): {detail[:1000]}")
    raise SystemExit(3)

encoded = (result.get("data") or [{}])[0].get("b64_json")
if not encoded:
    print("Image generation returned no image.")
    raise SystemExit(4)
with open(output_path, "wb") as handle:
    handle.write(base64.b64decode(encoded))
print(f"Generated premium story cover: {output_path}")
