import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = (ROOT / 'index.html').read_text(encoding='utf-8')


class VersionDisplayTests(unittest.TestCase):
    def test_version_file_has_all_games_unverified(self):
        data = json.loads((ROOT / 'versions_ja.json').read_text(encoding='utf-8'))
        self.assertEqual(set(data), {'genshin','wuwa','hsr','zzz','nte','arknights','endfield'})
        for row in data.values():
            self.assertIsNone(row['version'])
            self.assertEqual(row['status'], 'unverified')
            self.assertIsNone(row['official_url'])

    def test_safe_version_loading_and_fallback_exist(self):
        self.assertIn('async function loadVersions()', HTML)
        self.assertIn("row.status!=='official'", HTML)
        self.assertIn("'Ver.未確認'", HTML)
        self.assertIn("catch(e){console.warn('Version data unavailable',e)}", HTML)

    def test_version_validity_requires_dates_url_and_jp_region(self):
        self.assertIn('row.checked_at', HTML)
        self.assertIn('row.effective_from', HTML)
        self.assertIn("row.region==='JP'", HTML)
        self.assertIn('expires_at', HTML)

    def test_existing_display_features_remain(self):
        for token in ('hiddenEvents', 'enabledGames', 'enabledTypes', 'days===31', 'light=!light', 'border-width:3px'):
            self.assertIn(token, HTML)


if __name__ == '__main__':
    unittest.main()
