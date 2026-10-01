import json
import os
import tempfile
import urllib.parse
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import publish_facebook as facebook


class FakeResponse:
    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.data


class FacebookPublishingTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "META_PAGE_ID": "1234567890",
            "META_PAGE_ACCESS_TOKEN": "private-test-token",
            "META_GRAPH_API_VERSION": "v26.0",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_reel_upload_uses_page_session_then_publishes_with_story_caption(self):
        requests = []

        def fake_open(request, timeout=0):
            requests.append(request)
            if "rupload.facebook.com" in request.full_url:
                return FakeResponse({"success": True})
            if request.data and b"upload_phase=finish" in request.data:
                return FakeResponse({"success": True})
            return FakeResponse({"video_id": "123456789012345", "upload_url": "https://rupload.facebook.com/video-upload/v26.0/123456789012345"})

        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "short.mp4"
            video.write_bytes(b"test-video")
            with patch.object(facebook.urllib.request, "urlopen", side_effect=fake_open):
                result = facebook.publish_reel(video, {
                    "title": "היא נרדמה", "caption": "טיזר\n\nלקריאה: https://saliio.com/he/stories/she_fell_asleep"
                })

        self.assertEqual(result["videoId"], "123456789012345")
        self.assertEqual(len(requests), 3)
        self.assertIn("Bearer private-test-token", requests[0].headers["Authorization"])
        self.assertEqual(requests[1].headers["File_size"], "10")
        self.assertIn("OAuth private-test-token", requests[1].headers["Authorization"])
        finish = urllib.parse.parse_qs(requests[2].data.decode())
        self.assertEqual(finish["video_state"], ["PUBLISHED"])
        self.assertEqual(finish["title"], ["היא נרדמה"])

    def test_page_post_links_to_youtube_and_keeps_story_in_copy(self):
        captured = []

        def fake_open(request, timeout=0):
            captured.append(request)
            return FakeResponse({"id": "1234567890_9876543210"})

        metadata = {
            "title": "לא לספר למאיה", "teaser": "קבוצת משפחה מסתירה סוד.",
            "story_url": "https://saliio.com/he/stories/dont_tell_maya",
            "youtube_url": "https://youtube.com/shorts/abcdefghijk",
        }
        with patch.object(facebook.urllib.request, "urlopen", side_effect=fake_open):
            result = facebook.publish_page_post(metadata)
        body = captured[0].data.decode()
        post_fields = urllib.parse.parse_qs(body)
        self.assertEqual(post_fields["link"], ["https://youtube.com/shorts/abcdefghijk"])
        self.assertIn("לא לספר למאיה", post_fields["message"][0])
        self.assertEqual(result["postId"], "1234567890_9876543210")

    def test_api_version_rejects_malformed_values(self):
        os.environ["META_GRAPH_API_VERSION"] = "latest"
        with self.assertRaises(ValueError):
            facebook.api_version()


if __name__ == "__main__":
    unittest.main()
