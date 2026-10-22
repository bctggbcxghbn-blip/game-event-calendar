import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'games' / 'endfield' / 'diagnose_v84.py'
spec = importlib.util.spec_from_file_location('diagnose_v84', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class V84Tests(unittest.TestCase):
    def test_article_summary_extracts_title_and_date(self):
        result = module.article_summary({'title': 'テスト記事', 'publishTime': '2026-10-22', 'url': '/ja-jp/news/123'})
        self.assertEqual(result['title'], 'テスト記事')
        self.assertEqual(result['date_field'], '2026-10-22')
        self.assertEqual(result['link_field'], '/ja-jp/news/123')

    def test_find_records_nested_payload(self):
        result = module.find_records({'data': {'list': [{'id': 1, 'title': 'ニュース'}]}})
        self.assertTrue(any(item.get('title') == 'ニュース' for item in result))

    def test_safe_preview_does_not_dump_values(self):
        result = module.safe_preview({'token': 'private', 'data': []})
        self.assertEqual(result['type'], 'object')
        self.assertNotIn('private', str(result))

if __name__ == '__main__':
    unittest.main()
