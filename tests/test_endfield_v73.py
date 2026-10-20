import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'games' / 'endfield'))
from discover_v73 import parse_page, extract_candidates, discover, LIST, BASE

class Tests(unittest.TestCase):
    def test_links(self):
        self.assertIn(BASE + '/ja-jp/news/9560', parse_page('<a href="/ja-jp/news/9560">News</a>').links)
    def test_candidate(self):
        self.assertTrue(extract_candidates('<p>開催期間：2026/10/29 12:00～2026/11/19 11:59</p>'))
    def test_read_only(self):
        def fake(url):
            return '<a href="/ja-jp/news/9560">notice</a>' if url == LIST else '<p>開催期間：2026/10/29～2026/11/19</p>'
        result = discover(fake)
        self.assertEqual(result['auto_imported'], 0)
        self.assertEqual(result['article_count'], 1)

if __name__ == '__main__':
    unittest.main()
