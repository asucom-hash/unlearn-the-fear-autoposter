import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import publish_videos


class PublishVideoTests(unittest.TestCase):
    def test_approved_unlisted_youtube_video_becomes_public_without_duplicate(self):
        state = {
            "pending_short": {
                "quote_index": 24,
                "video_path": "reels/daily-0025.mp4",
                "youtube_id": "approved-video-id",
                "facebook_post_id": "facebook-id",
                "instagram_post_id": "instagram-id",
            }
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            docs = Path(temp_dir)
            video = docs / "reels" / "daily-0025.mp4"
            video.parent.mkdir(parents=True)
            video.write_bytes(b"test")
            with patch.dict(os.environ, {"PAGES_BASE_URL": "https://example.test/"}, clear=True), \
                 patch.object(publish_videos, "DOCS", docs), \
                 patch.object(publish_videos, "load_state", return_value=state), \
                 patch.object(publish_videos, "make_youtube_video_public") as make_public, \
                 patch.object(publish_videos, "upload_youtube") as upload, \
                 patch.object(publish_videos, "checkpoint"):
                publish_videos.publish("short", youtube_unlisted=False, youtube_only=True)
        make_public.assert_called_once_with("approved-video-id")
        upload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
