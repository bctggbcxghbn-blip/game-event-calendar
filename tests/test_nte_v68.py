import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'games'/'nte'))
from nte_discover_v68 import analyze

class V68Tests(unittest.TestCase):
    def test_empty(self):
        r=analyze('<html></html>',lambda url:'')
        self.assertEqual(r['articles'],[])
        self.assertEqual(r['auto_imported'],0)
    def test_detect_and_review(self):
        html='<a href="/jp/article/news/gamenews/20261019/123456.html">Ver.1.5 アップデートのお知らせ</a>'
        r=analyze(html,lambda url:'<p>イベント 2026年10月20日～2026年11月2日</p>')
        self.assertEqual(len(r['articles']),1)
        self.assertEqual(r['articles'][0]['status'],'review_required')
        self.assertGreaterEqual(r['articles'][0]['candidate_count'],1)
    def test_article_fetch_failure(self):
        html='<a href="/jp/article/news/gamenews/20261019/123456.html">Ver.1.5 アップデートのお知らせ</a>'
        def fail(url): raise RuntimeError('network')
        r=analyze(html,fail)
        self.assertEqual(r['articles'][0]['status'],'fetch_error')
