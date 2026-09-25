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
Create a premium cinematic photographic background for a story poster.
Story title for context only: {title}
Genre: {genre}
Premise: {teaser}
Deep blacks, red accents, warm practical lighting, realistic atmospheric scenery.
Keep the focal scene in the lower half and leave dark uncluttered space for typography.
NO text, letters, numbers, logos, typography, chat bubbles, UI, ratings or watermarks.
The final typography and brand will be composed separately using real fonts.
"""

payload = json.dumps({
    "model": "gpt-image-1",
    "size": "1024x1536",
    "quality": "high",
    "output_format": "png",
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
