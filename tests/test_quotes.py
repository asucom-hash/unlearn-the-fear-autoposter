import sys,unittest,json
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from art import render_quote
ROOT=Path(__file__).resolve().parents[1]
class TestQuotes(unittest.TestCase):
    def test_bank(self):
        q=json.loads((ROOT/'quotes.json').read_text())
        self.assertEqual(len(q),180)
        self.assertEqual(len(q),len(set(q)))
    def test_art(self):
        q=json.loads((ROOT/'quotes.json').read_text())
        with TemporaryDirectory() as tmp:
            for i in (0,1,2,45,90,135,179):
                p=Path(tmp)/str(i)
                render_quote(q[i],i,p)
                with Image.open(p) as im:
                    self.assertEqual(im.size,(1080,1080))
                    self.assertEqual(im.format,'JPEG')
