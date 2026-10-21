import importlib.util
from pathlib import Path
import unittest

FILE=Path(__file__).resolve().parents[1]/'games/endfield/diagnose_v79.py'
spec=importlib.util.spec_from_file_location('diagnose_v79',FILE)
v79=importlib.util.module_from_spec(spec);spec.loader.exec_module(v79)

class V79Tests(unittest.TestCase):
    def test_first_party_only(self):
        html='<script src="/assets/app.js"></script><script src="https://evil.example/x.js"></script>'
        self.assertEqual(v79.first_party_assets(html), ['https://endfield.gryphline.com/assets/app.js'])
    def test_hints(self):
        self.assertIn('/api/news/list',v79.hints('fetch("/api/news/list")'))
    def test_run_read_only(self):
        def fake(url):
            if url.endswith('/ja-jp/news'): return '<script src="/a.js"></script>',200,url
            return 'fetch("/api/news/list")',200,url
        report=v79.run(fake)
        self.assertEqual(report['events_added'],0)
        self.assertIn('/api/news/list',report['endpoint_candidates'])

if __name__=='__main__': unittest.main()
