import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from tools.update_versions import accept, merge, update, version_key


TODAY = dt.date(2026, 11, 19)


def candidate(**overrides):
    row = {'game': 'genshin', 'version': '7.1', 'status': 'official',
           'official_url': 'https://example.com/jp/version',
           'checked_at': '2026-11-18T00:00:00+09:00',
           'effective_from': '2026-11-01', 'expires_at': None, 'region': 'JP'}
    row.update(overrides)
    return row


class VersionUpdateTests(unittest.TestCase):
    def test_accepts_verified_official_candidate(self):
        self.assertIsNotNone(accept(candidate(), TODAY))

    def test_rejects_invalid_url_missing_start_future_and_expired(self):
        for row in (candidate(official_url='http://example.com'), candidate(effective_from=None),
                    candidate(effective_from='2026-12-01'), candidate(expires_at='2026-11-19')):
            self.assertIsNone(accept(row, TODAY))

    def test_rejects_non_official_and_non_jp(self):
        self.assertIsNone(accept(candidate(status='unverified'), TODAY))
        self.assertIsNone(accept(candidate(region='US'), TODAY))

    def test_numeric_version_order_and_old_protection(self):
        self.assertGreater(version_key('7.10'), version_key('7.2'))
        old = {'genshin': candidate(version='7.10'), 'wuwa': {}}
        result = merge(old, [candidate(version='7.2')], TODAY)
        self.assertEqual(result['genshin']['version'], '7.10')

    def test_same_version_is_idempotent(self):
        old = {'genshin': candidate(), 'wuwa': {}}
        self.assertEqual(merge(old, [candidate()], TODAY), merge(old, [candidate()], TODAY))

    def test_failed_or_unverified_candidates_preserve_existing(self):
        old = {'genshin': candidate(), 'wuwa': {}}
        result = merge(old, [candidate(status='unverified'), candidate(game='wuwa', version='9.9', region='US')], TODAY)
        self.assertEqual(result['genshin']['version'], '7.1')
        self.assertEqual(result['wuwa'], {})

    def test_corrupt_json_stops_without_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'versions.json'
            path.write_text('{broken', encoding='utf-8')
            self.assertFalse(update(path, today=TODAY))
            self.assertEqual(path.read_text(encoding='utf-8'), '{broken')


if __name__ == '__main__':
    unittest.main()
