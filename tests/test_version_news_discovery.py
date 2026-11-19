import datetime as dt
import unittest

from tools.discover_version_news import discover_candidates, discover_links


LISTING = '''<a href="/jp/main/news/1">Ver.3.8 日本版アップデート</a>
<a href="https://example.com/news/2">Ver.9.9</a>
<a href="/jp/main/news/1">Ver.3.8 日本版アップデート</a>'''
ARTICLE = '<html lang="ja"><title>Ver.3.8</title><p>日本版は2026年11月1日から適用</p></html>'


class VersionNewsDiscoveryTests(unittest.TestCase):
    def test_discovers_unique_official_links_only(self):
        links = discover_links('wuwa', LISTING, 'https://wutheringwaves.kurogames.com/jp/main/news')
        self.assertEqual(links, ['https://wutheringwaves.kurogames.com/jp/main/news/1'])

    def test_converts_article_to_candidate_and_deduplicates(self):
        rows = discover_candidates('wuwa', LISTING, 'https://wutheringwaves.kurogames.com/jp/main/news',
                                   {'https://wutheringwaves.kurogames.com/jp/main/news/1': ARTICLE},
                                   '2026-11-19T00:00:00+09:00', today=dt.date(2026, 11, 19))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['region'], 'JP')

    def test_rejects_non_official_listing_and_malformed_html(self):
        self.assertEqual(discover_links('wuwa', LISTING, 'https://example.com/news'), [])
        self.assertEqual(discover_links('wuwa', '<div>no anchors', 'https://wutheringwaves.kurogames.com/jp/main/news'), [])

    def test_arknights_is_not_auto_versioned(self):
        self.assertEqual(discover_links('arknights', LISTING, 'https://arknights.jp/news'), [])


if __name__ == '__main__':
    unittest.main()
