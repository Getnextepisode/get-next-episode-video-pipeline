#!/usr/bin/env python3
"""Publish a generated SALIIO Short as a Facebook Page Reel or teaser post."""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def api_version():
    version = os.environ.get("META_GRAPH_API_VERSION", "v26.0")
    if not re.fullmatch(r"v\d+\.\d+", version):
        raise ValueError("META_GRAPH_API_VERSION must look like v26.0")
    return version


def graph_request(method, path, fields=None):
    token = os.environ.get("META_PAGE_ACCESS_TOKEN", "")
    page_id = os.environ.get("META_PAGE_ID", "")
    if not token or not page_id:
        raise ValueError("META_PAGE_ID and META_PAGE_ACCESS_TOKEN are required")
    url = f"https://graph.facebook.com/{api_version()}/{path}"
    body = urllib.parse.urlencode(fields or {}).encode() if fields is not None else None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Meta API request failed (HTTP {error.code}): {detail}") from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"Meta API request failed: {error.reason}") from None


def safe_slug(value):
    slug = re.sub(r"[^a-z0-9_]+", "", value.lower())
    if not slug:
        raise ValueError("manifest must contain a valid story id")
    return slug


def load_metadata(manifest_path, youtube_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    story_id = safe_slug(str(manifest.get("story", "")))
    title = str(manifest.get("title") or "SALIIO")[:100]
    teaser = str(manifest.get("teaser") or "")[:400]
    story_url = f"https://saliio.com/he/stories/{story_id}?utm_source=facebook&utm_medium=reel&utm_campaign={story_id}"
    youtube_url = None
    if Path(youtube_path).is_file():
        video_id = json.loads(Path(youtube_path).read_text(encoding="utf-8")).get("videoId")
        if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", str(video_id)):
            youtube_url = f"https://youtube.com/shorts/{video_id}"
    caption_parts = [part for part in (teaser, f"המשיכו לקרוא ולגלות מה מחכה לכם בפרק הבא: {story_url}", f"לצפייה גם ב־YouTube: {youtube_url}" if youtube_url else "") if part]
    return {"story_id": story_id, "title": title, "teaser": teaser, "story_url": story_url, "youtube_url": youtube_url, "caption": "\n\n".join(caption_parts)}


def publish_reel(video_path, metadata):
    page_id = urllib.parse.quote(os.environ["META_PAGE_ID"], safe="")
    video_path = Path(video_path)
    size = video_path.stat().st_size
    started = graph_request("POST", f"{page_id}/video_reels", {"upload_phase": "start"})
    video_id = str(started.get("video_id", ""))
    upload_url = str(started.get("upload_url", ""))
    if not re.fullmatch(r"\d{8,32}", video_id) or not upload_url.startswith("https://rupload.facebook.com/"):
        raise RuntimeError("Meta did not return a valid Reel upload session")

    token = os.environ["META_PAGE_ACCESS_TOKEN"]
    request = urllib.request.Request(upload_url, data=video_path.read_bytes(), headers={
        "Authorization": f"OAuth {token}",
        "offset": "0",
        "file_size": str(size),
        "Content-Type": "application/octet-stream",
    }, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            uploaded = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Meta Reel upload failed (HTTP {error.code}): {detail}") from None
    if uploaded.get("success") is not True:
        raise RuntimeError("Meta did not confirm the Reel upload")

    finished = graph_request("POST", f"{page_id}/video_reels", {
        "video_id": video_id,
        "upload_phase": "finish",
        "video_state": "PUBLISHED",
        "title": metadata["title"],
        "description": metadata["caption"],
    })
    if finished.get("success") is not True:
        raise RuntimeError("Meta did not confirm Reel publication")
    return {"videoId": video_id, "url": f"https://www.facebook.com/reel/{video_id}"}


def publish_page_post(metadata):
    page_id = urllib.parse.quote(os.environ["META_PAGE_ID"], safe="")
    link = metadata["youtube_url"] or metadata["story_url"]
    message = f"{metadata['title']}\n\n{metadata['teaser']}\n\nהמשיכו לקרוא ולגלות מה מחכה לכם בפרק הבא: {metadata['story_url']}"
    result = graph_request("POST", f"{page_id}/feed", {"message": message, "link": link})
    post_id = str(result.get("id", ""))
    if not re.fullmatch(r"\d{5,32}(?:_\d{5,32})?", post_id):
        raise RuntimeError("Meta did not return a valid Page post ID")
    return {"postId": post_id, "url": f"https://www.facebook.com/{post_id}"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=("reel", "post"))
    parser.add_argument("--video", default="build/story-short.mp4")
    parser.add_argument("--manifest", default="build/manifest.json")
    parser.add_argument("--youtube", default="build/youtube-upload.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    metadata = load_metadata(args.manifest, args.youtube)
    result = publish_reel(args.video, metadata) if args.target == "reel" else publish_page_post(metadata)
    result["storyId"] = metadata["story_id"]
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(f"Facebook {args.target} published: {result.get('url')}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Facebook publishing failed: {error}", file=sys.stderr)
        sys.exit(1)
