import datetime as dt
import unittest

from tools.discover_version_news import discover_endfield_body_candidates


LISTING = '''
<a href="/ja-jp/news/9560">お知らせ</a>
<a href="/ja-jp/news/7012">特別スカウト</a>
<a href="https://example.com/news/1">Ver.9.9</a>
'''
URL = 'https://endfield.gryphline.com/ja-jp/news/9560'


class EndfieldBodyFallbackTests(unittest.TestCase):
    def test_numeric_version_in_body_without_title_hint(self):
        pages = {URL: '<html lang="ja"><p>新バージョン Ver.1.2.3</p><p>Asiaサーバー：2026/11/01開始</p></html>'}
        rows, stats = discover_endfield_body_candidates(
            LISTING, 'https://endfield.gryphline.com/ja-jp/news', pages,
            '2026-11-20T00:00:00+09:00', today=dt.date(2026, 11, 20))
        self.assertEqual(rows[0]['version'], '1.2.3')
        self.assertEqual(stats['body_candidates'], 1)

    def test_proper_name_only_is_not_numeric_candidate(self):
        pages = {URL: '<html lang="ja"><p>「丹青渡」バージョンアップデート</p><p>Asia：2026/11/01開始</p></html>'}
        rows, stats = discover_endfield_body_candidates(
            LISTING, 'https://endfield.gryphline.com/ja-jp/news', pages,
            '2026-11-20T00:00:00+09:00', today=dt.date(2026, 11, 20))
        self.assertEqual(rows, [])
        self.assertEqual(stats['rejected_proper_name_only'], 1)

    def test_missing_or_future_date_and_non_official_are_rejected(self):
        pages = {
            URL: '<html lang="ja"><p>Ver.1.2.3 Asia</p></html>',
            'https://endfield.gryphline.com/ja-jp/news/7012': '<p>Ver.1.2.4 日本 2099/01/01</p>',
        }
        rows, stats = discover_endfield_body_candidates(
            LISTING, 'https://endfield.gryphline.com/ja-jp/news', pages,
            '2026-11-20T00:00:00+09:00', today=dt.date(2026, 11, 20))
        self.assertEqual(rows, [])
        self.assertGreaterEqual(stats['rejected_no_effective_date_or_region'], 1)

    def test_article_limit_is_twenty_and_fetch_failure_is_safe(self):
        listing = ''.join(f'<a href="/ja-jp/news/{i}">記事</a>' for i in range(30))
        rows, stats = discover_endfield_body_candidates(
            listing, 'https://endfield.gryphline.com/ja-jp/news', {},
            '2026-11-20T00:00:00+09:00', today=dt.date(2026, 11, 20), max_articles=20)
        self.assertEqual(rows, [])
        self.assertEqual(stats['article_urls_considered'], 20)
        self.assertEqual(stats['article_fetch_failures'], 20)


if __name__ == '__main__':
    unittest.main()
