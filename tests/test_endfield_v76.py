import importlib.util
from pathlib import Path
import unittest

FILE=Path(__file__).resolve().parents[1]/'games/endfield/monitor_v76.py'
spec=importlib.util.spec_from_file_location('monitor_v76',FILE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class TestMonitor(unittest.TestCase):
    def test_notice_links_unique(self):
        links=['/ja-jp/news/123','https://endfield.gryphline.com/ja-jp/news/123','/ja-jp/news/456','https://elsewhere.com/ja-jp/news/789']
        self.assertEqual(m.notice_urls(links),[m.BASE_ARTICLE,m.ROOT+'/ja-jp/news/123',m.ROOT+'/ja-jp/news/456'])
    def test_no_auto_approval_even_if_date_present(self):
        result=m.scan([{'id':'x','name':'ミンホ「人煙の牽く天河」','end_condition':'次回メンテ前'}],
                      {'https://example.com':['人煙の牽く天河','開催期間：2026/11/05 12:00 ～ 2026/12/03 11:59']})
        self.assertEqual(result[0]['status'],'manual_review')
        self.assertIsNone(result[0]['verified_end'])
    def test_read_only_and_fetch_failures(self):
        def fetch(url):
            if url==m.INDEX: return '<a href="/ja-jp/news/123">News</a>'
            if url==m.BASE_ARTICLE: return '<p>俗世の縁</p><p>メンテナンス前</p>'
            raise OSError('offline')
        report=m.run(fetcher=fetch)
        self.assertEqual(report['automatically_approved'],0)
        self.assertEqual(report['events_added'],0)
        self.assertEqual(report['articles_checked'],1)
        self.assertEqual(len(report['fetch_errors']),1)

if __name__=='__main__': unittest.main()
