import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]/'games'/'endfield'
sys.path.insert(0,str(ROOT))
import monitor_v77 as m

class TestV77(unittest.TestCase):
    def test_discover_from_sitemap_and_json(self):
        pages={'a':'<loc>https://endfield.gryphline.com/ja-jp/news/1234</loc>',
               'b':r'{"url":"\/ja-jp\/news\/5678"}'}
        urls=m.discover(pages)
        self.assertIn(m.ROOT+'/ja-jp/news/1234',urls)
        self.assertIn(m.ROOT+'/ja-jp/news/5678',urls)
    def test_dedup(self):
        self.assertEqual(m.discover({'a':'/ja-jp/news/1234 /ja-jp/news/1234'}).count(m.ROOT+'/ja-jp/news/1234'),1)
    def test_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'pending.json';p.write_text(json.dumps([{'id':'a','name':'イベントA','end_condition':'未定'}]),encoding='utf-8')
            def fake(url):
                if url.endswith('/ja-jp/news'): return '<a href="/ja-jp/news/1234">a</a>'
                if url.endswith('/1234'): return '<p>イベントA 2026年12月3日</p>'
                return ''
            r=m.run(fake,p)
            self.assertEqual(r['automatically_approved'],0)
            self.assertIsNone(r['results'][0]['verified_end'])
            self.assertEqual(r['articles_checked'],2)
if __name__=='__main__': unittest.main()
