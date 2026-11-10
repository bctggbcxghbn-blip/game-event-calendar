import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'games/hsr/hsr_gacha_dedupe.py'

class TestV94(unittest.TestCase):
    def test_compiles(self):
        compile(SRC.read_text(encoding='utf-8'), str(SRC), 'exec')
    def test_stale_only_kept(self):
        t=SRC.read_text(encoding='utf-8')
        self.assertIn('stale-only ID; retained unchanged',t)
        self.assertIn('continue',t)
    def test_no_write_on_no_change(self):
        t=SRC.read_text(encoding='utf-8')
        self.assertIn('if not remove:',t)
        self.assertIn('events.json unchanged',t)

if __name__ == '__main__': unittest.main()
