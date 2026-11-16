import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from video_pipeline import LONG_SHAPES, long_transcript, short_transcript, topic_for


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

if __name__ == "__main__":
    unittest.main()
