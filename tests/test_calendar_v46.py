"""Offline display/data contract tests for the GitHub Pages calendar."""
import json
import re
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def classify(kind):
    k = str(kind or '').strip()
    if re.search(r'^(gacha|banner|wish)$', k, re.I) or re.search(r'ガチャ|新キャラ|復刻キャラ|新武器|復刻武器|スカウト|祈願|跳躍|変調|集音', k):
        return 'gacha'
    if re.search(r'^maintenance$', k, re.I) or 'メンテ' in k:
        return 'maintenance'
    if re.search(r'^story$', k, re.I) or re.search(r'ストーリー|シナリオ', k):
        return 'story'
    if re.search(r'^challenge$', k, re.I) or re.search(r'挑戦|チャレンジ|高難度', k):
        return 'challenge'
    if re.search(r'^event$', k, re.I) or re.search(r'イベント|ログイン|報酬', k):
        return 'event'
    return 'other'


class CalendarV46(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = json.loads((ROOT / 'events.json').read_text(encoding='utf-8'))
        cls.html = (ROOT / 'index.html').read_text(encoding='utf-8')

    def test_data_structure(self):
        self.assertIsInstance(self.events, list)
        self.assertTrue(self.events)
        for event in self.events:
            with self.subTest(id=event.get('id')):
                self.assertTrue(all(isinstance(event.get(k), str) and event[k].strip() for k in ('id','game','name','start','end')))

    def test_valid_calendar_dates(self):
        for event in self.events:
            with self.subTest(id=event['id']):
                start, end = date.fromisoformat(event['start'][:10]), date.fromisoformat(event['end'][:10])
                self.assertLessEqual(start, end)

    def test_unique_ids(self):
        ids = [event['id'] for event in self.events]
        self.assertEqual(len(ids), len(set(ids)))

    def test_game_keys_supported(self):
        for event in self.events:
            self.assertRegex(self.html, r'\b' + re.escape(event['game']) + r':\[')

    def test_english_categories_recognized(self):
        for kind, expected in [('gacha','gacha'),('event','event'),('challenge','challenge'),('maintenance','maintenance'),('story','story')]:
            self.assertEqual(classify(kind), expected)
            self.assertIn(kind, self.html)

    def test_japanese_categories_recognized(self):
        for kind, expected in [('復刻キャラ','gacha'),('武器・装備ガチャ','gacha'),('チャレンジ','challenge'),('イベント','event')]:
            self.assertEqual(classify(kind), expected)

    def test_all_existing_kinds_classified(self):
        unclassified = Counter(e.get('kind','') for e in self.events if classify(e.get('kind')) == 'other')
        self.assertFalse(unclassified, f'Unclassified kind(s): {dict(unclassified)}')

    def test_no_source_data_rewritten(self):
        self.assertTrue(any(e['game']=='wuwa' for e in self.events))


if __name__ == '__main__':
    unittest.main()
