import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('update_events', ROOT / 'update_events.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class WuwaActivityOverrideTests(unittest.TestCase):
    def test_official_period_override_is_exact_and_jst(self):
        blob = json.dumps([{'activities': [
            {'name': 'Where the Wind Leads', 'startTime': '2026-12-03T00:00:00', 'endTime': '2026-12-21T23:59:00'}
        ]}])
        rows = mod.activity_events(blob, {'game': 'wuwa'})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['start'], '2026-12-07')
        self.assertEqual(rows[0]['end'], '2026-12-21')
        self.assertEqual(rows[0]['source_status'], '公式日本語告知・JST確認済み')
        self.assertIn('/5785', rows[0]['official_url'])

    def test_same_name_different_period_is_not_overridden(self):
        blob = json.dumps([{'activities': [
            {'name': 'Where the Wind Leads', 'startTime': '2027-01-03T00:00:00', 'endTime': '2027-01-21T23:59:00'}
        ]}])
        rows = mod.activity_events(blob, {'game': 'wuwa'})
        self.assertEqual(rows[0]['start'], '2027-01-03')
        self.assertEqual(rows[0]['source_status'], '外部API・要確認')


if __name__ == '__main__':
    unittest.main()
