import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.verify_version_sources import audit, write_report


class VerifyVersionSourcesTests(unittest.TestCase):
    def test_all_failures_still_produce_report(self):
        with patch('tools.verify_version_sources.fetch', return_value={'ok': False, 'reason': 'timeout', 'status': None}):
            report = audit(timeout=1)
        self.assertEqual(set(report['games']), {'genshin', 'wuwa', 'hsr', 'zzz', 'nte', 'endfield'})
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            write_report(report, out / 'report.json', out / 'report.md')
            self.assertTrue(json.loads((out / 'report.json').read_text(encoding='utf-8'))['read_only'])
            self.assertTrue((out / 'report.md').exists())

    def test_redirect_is_rejected_and_other_games_continue(self):
        calls = iter([
            {'ok': True, 'status': 200, 'final_url': 'https://redirect.invalid', 'html': ''},
            *([{'ok': False, 'reason': 'timeout', 'status': None}] * 5),
        ])
        with patch('tools.verify_version_sources.fetch', side_effect=lambda *a, **k: next(calls)):
            report = audit(timeout=1)
        self.assertEqual(report['games']['genshin']['status'], 'failed')
        self.assertIn('wuwa', report['games'])

    def test_report_contains_no_event_data_write_path(self):
        with patch('tools.verify_version_sources.fetch', return_value={'ok': False, 'reason': 'timeout', 'status': None}):
            report = audit(timeout=1)
        self.assertTrue(report['read_only'])
        self.assertNotIn('events.json', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
