import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('diagnose_v80', ROOT / 'games/endfield/diagnose_v80.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestV80(unittest.TestCase):
    def test_cdn_asset_from_inline_next_data(self):
        html = '<script>"https://web-static.hg-cdn.com/endfield/official-v4/_next/static/chunks/app/%5Blang%5D/(main)/(subpage)/news/page-845bebead983deba.js"</script>'
        assets = mod.assets_from_html(html)
        self.assertEqual(len(assets), 1)
        self.assertTrue(assets[0].endswith('.js'))

    def test_disallow_other_hosts(self):
        self.assertFalse(mod.allowed('https://untrusted.example.com/news.js'))
        self.assertTrue(mod.allowed('https://web-static.hg-cdn.com/endfield/news.js'))

    def test_offline_report(self):
        def fake(url):
            if url == mod.NEWS:
                return '<script src="https://web-static.hg-cdn.com/endfield/news/page-test.js"></script>', 200, url
            return 'fetch("https://web-api.gryphline.com/news/list")', 200, url
        report = mod.run(fetcher=fake, max_assets=2)
        self.assertGreaterEqual(len(report['assets']), 1)
        self.assertTrue(any('/news/list' in s for s in report['endpoint_candidates']))
        self.assertEqual(report['events_added'], 0)

if __name__ == '__main__':
    unittest.main()
