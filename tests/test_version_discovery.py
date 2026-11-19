import datetime as dt
import unittest

from tools.discover_versions import discover_html


TODAY = dt.date(2026, 11, 19)
HTML = '<html lang="ja"><title>Ver.3.8アップデート</title><p>日本版は2026年11月1日から適用</p></html>'


class VersionDiscoveryTests(unittest.TestCase):
    def test_official_japanese_article_becomes_candidate(self):
        row = discover_html('wuwa', HTML, 'https://wutheringwaves.kurogames.com/jp/main/news/1', '2026-11-19T00:00:00+09:00', TODAY)
        self.assertEqual(row['version'], '3.8')
        self.assertEqual(row['effective_from'], '2026-11-01')

    def test_future_version_is_not_current(self):
        future = HTML.replace('2026年11月1日', '2026年12月1日')
        self.assertIsNone(discover_html('nte', future, 'https://nte.perfectworld.com/jp/article/1', '2026-11-19T00:00:00+09:00', TODAY))

    def test_requires_allowlisted_official_jp_source(self):
        self.assertIsNone(discover_html('wuwa', HTML, 'https://example.com/jp/news/1', '2026-11-19T00:00:00+09:00', TODAY))
        self.assertIsNone(discover_html('arknights', HTML, 'https://arknights.jp/news/1', '2026-11-19T00:00:00+09:00', TODAY))

    def test_requires_explicit_version_date_and_jp_context(self):
        self.assertIsNone(discover_html('zzz', '<p>アップデート 2026/11/01</p>', 'https://zenless.hoyoverse.com/ja-jp/news/1', '2026-11-19', TODAY))
        self.assertIsNone(discover_html('zzz', '<p>Version 3.8</p>', 'https://zenless.hoyoverse.com/ja-jp/news/1', '2026-11-19', TODAY))


if __name__ == '__main__':
    unittest.main()
