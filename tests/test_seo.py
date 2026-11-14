import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from seo import build_post

class TestPostMetadata(unittest.TestCase):
    def test_all_180_quotes_have_unique_readable_titles_and_safe_captions(self):
        quotes = json.loads((ROOT / "quotes.json").read_text())
        headlines = set()
        tag_banks = set()
        for i, quote in enumerate(quotes):
            headline, caption = build_post(quote, i)
            self.assertTrue(caption.startswith(headline + " 🖤💛"))
            self.assertIn(quote, caption)
            self.assertIn("Follow Unlearn The Fear", caption)
            self.assertLessEqual(len(caption), 2200)
            tags = re.findall(r"#[A-Za-z][A-Za-z0-9]*", caption)
            self.assertEqual(len(tags), 5, f"Quote {i}: expected exactly 5 tags")
            self.assertEqual(len(set(tags)), 5)
            self.assertEqual(tags[0], "#UnlearnTheFear")
            headlines.add(headline)
            tag_banks.update(tags)
        self.assertEqual(len(headlines), len(quotes))
        self.assertGreaterEqual(len(tag_banks), 65)

    def test_courage_example_has_search_terms(self):
        headline, caption = build_post(
            "Courage is not the absence of fear. It is the decision to move anyway.", 1
        )
        self.assertIn("Overcome Fear", headline)
        self.assertIn("confidence", caption.lower())
        self.assertIn("#UnlearnTheFear", caption)

if __name__ == "__main__":
    unittest.main()
