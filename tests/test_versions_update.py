import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from tools.update_versions import accept, endfield_candidate_from_audit, merge, update, version_key


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

    def test_endfield_released_candidate_is_diagnostic_data_only(self):
        report = {'checked_at': '2026-11-26T00:00:00+09:00', 'named_version_groups': [{
            'named_version': 'キノコ菌グ！？君との大冒険！',
            'latest_released_candidate': {'cid': '7011', 'article_url': 'https://endfield.gryphline.com/ja-jp/news/7011',
                                          'announced_release_date': '2026-11-25'},
            'evidence': [{'cid': '7011', 'article_url': 'https://endfield.gryphline.com/ja-jp/news/7011'}]}]}
        rows = endfield_candidate_from_audit(report, TODAY)
        self.assertEqual(rows, [])
        rows = endfield_candidate_from_audit(report, dt.date(2026, 11, 26))
        self.assertEqual(rows[0]['version_kind'], 'named')
        self.assertEqual(accept(rows[0], dt.date(2026, 11, 26))['release_name'], 'キノコ菌グ！？君との大冒険！')

    def test_endfield_older_named_candidate_cannot_roll_back(self):
        old = {'endfield': {'version_kind': 'named', 'release_name': '新',
                            'announced_release_date': '2026-11-25'}, 'genshin': {}}
        newer = {'game': 'endfield', 'version_kind': 'named', 'release_name': '旧',
                 'status': 'released_candidate', 'official_url': 'https://endfield.gryphline.com/ja-jp/news/1',
                 'checked_at': '2026-11-26', 'announced_release_date': '2026-11-20', 'region': 'JP'}
        self.assertEqual(merge(old, [newer], dt.date(2026, 11, 26))['endfield']['release_name'], '新')


if __name__ == '__main__':
    unittest.main()
