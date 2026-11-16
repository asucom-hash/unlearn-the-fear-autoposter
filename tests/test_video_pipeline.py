import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from video_pipeline import (
    LONG_SHAPES,
    caption_rows,
    emphasise_ass,
    long_transcript,
    make_ass_captions,
    short_transcript,
    topic_for,
)


class VideoPipelineTests(unittest.TestCase):
    def test_short_script_has_original_guidance(self):
        text = short_transcript("Take the next step.", "Courage")
        self.assertIn("Take the next step.", text)
        self.assertGreater(len(text.split()), 30)

    def test_long_scripts_are_substantive(self):
        quotes = [f"Original reflection number {n}." for n in range(10)]
        text = long_transcript(LONG_SHAPES[0], quotes)
        self.assertGreater(len(text.split()), 700)
        self.assertIn("Original reflection number 9.", text)

    def test_topics_cycle(self):
        self.assertEqual(topic_for(0)[0], "Courage")
        self.assertEqual(topic_for(18)[0], "Healing")

    def test_vertical_caption_cards_stay_narrow_and_use_lavender_emphasis(self):
        rows = caption_rows("Release the need to understand every goodbye before you move on.", vertical=True)
        self.assertTrue(rows)
        self.assertTrue(all(len(row) <= 32 for row in rows))
        self.assertIn(r"{\c&H00ED9CB7&}", emphasise_ass(rows[0]))

    def test_ass_caption_card_declares_safe_vertical_margins(self):
        output = ROOT / ".test-captions.ass"
        self.addCleanup(output.unlink, missing_ok=True)
        make_ass_captions("Take one gentle step toward your future.", 8, output, width=1080, height=1920)
        ass = output.read_text(encoding="utf-8")
        self.assertIn("PlayResX: 1080", ass)
        self.assertIn(",88,88,390,1", ass)
        self.assertIn("&H004AD4F7", ass)

if __name__ == "__main__":
    unittest.main()
