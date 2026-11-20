import unittest

from tools.discover_version_news import diagnose_endfield_links


class EndfieldUrlDiagnosticsTests(unittest.TestCase):
    def test_classifies_paths_and_sanitizes_query(self):
        html = '''
        <a href="/ja-jp/news/9560">article</a>
        <a href="/ja-jp/news">index</a>
        <a href="/ja-jp/news?id=9560&token=secret">query</a>
        <a href="/other/9560">wrong</a>
        <a href="/ja-jp/news/not-an-id">bad</a>
        <a href="https://example.com/ja-jp/news/1">external</a>
        <script>const u="https://endfield.gryphline.com/ja-jp/news/7012"</script>
        '''
        result = diagnose_endfield_links(html, 'https://endfield.gryphline.com/ja-jp/news')
        self.assertEqual(result['article_path_links'], 1)
        self.assertEqual(result['rejected_wrong_path'], 1)
        self.assertEqual(result['rejected_invalid_article_id'], 1)
        self.assertEqual(result['script_json_article_urls'], 1)
        samples = [item['url'] for item in result['official_link_samples']]
        self.assertIn('https://endfield.gryphline.com/ja-jp/news?id=9560', samples)
        self.assertNotIn('token=secret', ''.join(samples))

    def test_untrusted_listing_returns_empty_diagnostics(self):
        result = diagnose_endfield_links(
            '<a href="https://endfield.gryphline.com/ja-jp/news/9560">x</a>',
            'https://example.com/news')
        self.assertEqual(result['official_link_samples'], [])
        self.assertEqual(result['article_path_links'], 0)


if __name__ == '__main__':
    unittest.main()
