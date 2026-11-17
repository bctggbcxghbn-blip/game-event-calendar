import json
import pathlib
import unittest

from tools.verify_calendar import allowed_wuwa_wind_change


ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = 'activity-dfcbb9cc10082b3a37e3'


class VerifyCalendarWuwaAllowlistTests(unittest.TestCase):
    def setUp(self):
        self.old = [{'id': TARGET, 'game': 'wuwa', 'name': '風のゆくさき',
                     'start': '2026-12-03', 'end': '2026-12-21',
                     'source_status': '外部API・要確認', 'original_name': 'Where the Wind Leads'}]
        self.new = [{'id': TARGET, 'game': 'wuwa', 'name': '風のゆくさき',
                     'start': '2026-12-07', 'end': '2026-12-21',
                     'source_status': '公式日本語告知・JST確認済み',
                     'original_name': 'Where the Wind Leads',
                     'official_url': 'https://wutheringwaves.kurogames.com/jp/main/news/detail/5785'}]

    def test_exact_reviewed_change_is_allowed(self):
        self.assertTrue(allowed_wuwa_wind_change(json.dumps(self.old).encode(), json.dumps(self.new).encode()))

    def test_other_event_change_is_rejected(self):
        changed = self.new + [{'id': 'other', 'game': 'wuwa', 'name': '別', 'start': '2026-01-01', 'end': '2026-01-02'}]
        self.assertFalse(allowed_wuwa_wind_change(json.dumps(self.old).encode(), json.dumps(changed).encode()))

    def test_add_remove_field_or_url_change_is_rejected(self):
        bad = json.loads(json.dumps(self.new))
        bad[0]['official_url'] = 'https://example.invalid'
        self.assertFalse(allowed_wuwa_wind_change(json.dumps(self.old).encode(), json.dumps(bad).encode()))
        bad = json.loads(json.dumps(self.new))
        bad[0]['kind'] = 'ガチャ'
        self.assertFalse(allowed_wuwa_wind_change(json.dumps(self.old).encode(), json.dumps(bad).encode()))

    def test_other_game_and_index_are_not_part_of_allowlist(self):
        other = [{'id': TARGET, 'game': 'hsr', 'name': '風のゆくさき', 'start': '2026-12-07', 'end': '2026-12-21',
                  'source_status': '公式日本語告知・JST確認済み', 'official_url': self.new[0]['official_url']}]
        self.assertFalse(allowed_wuwa_wind_change(json.dumps(self.old).encode(), json.dumps(other).encode()))


if __name__ == '__main__':
    unittest.main()
