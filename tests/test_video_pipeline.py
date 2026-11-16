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
    make_original_nature_fallback,
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

    def test_caption_timeline_uses_the_voice_duration_not_visual_hold(self):
        output = ROOT / ".test-caption-timing.ass"
        self.addCleanup(output.unlink, missing_ok=True)
        make_ass_captions("First spoken thought. Second spoken thought.", 12.9, output, width=1080, height=1920)
        dialogue = [line for line in output.read_text(encoding="utf-8").splitlines() if line.startswith("Dialogue:")]
        self.assertTrue(dialogue)
        self.assertNotIn("0:00:28", "\n".join(dialogue))
        self.assertIn("0:00:12.", dialogue[-1])

    def test_short_caption_cards_can_leave_the_final_spoken_line_clean(self):
        output = ROOT / ".test-final-line.ass"
        self.addCleanup(output.unlink, missing_ok=True)
        make_ass_captions(
            "First visible line. Final spoken line.",
            8,
            output,
            width=1080,
            height=1920,
            omit_final_sentence=True,
        )
        ass = output.read_text(encoding="utf-8")
        self.assertIn("First ", ass)
        self.assertIn("line", ass)
        self.assertNotIn("Final spoken line", ass)

    def test_original_visual_fallback_is_portrait_and_attributable(self):
        output = ROOT / ".test-fallback.jpg"
        self.addCleanup(output.unlink, missing_ok=True)
        credit = make_original_nature_fallback(output, choice=3)
        from PIL import Image
        with Image.open(output) as image:
            self.assertEqual(image.size, (1080, 1920))
        self.assertEqual(credit["creator"], "Unlearn The Fear")

if __name__ == "__main__":
    unittest.main()
