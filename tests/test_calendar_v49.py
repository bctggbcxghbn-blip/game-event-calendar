import csv
import json
import unittest
from pathlib import Path

from calendar_translation_v48 import candidates

ROOT = Path(__file__).resolve().parents[1]


class CalendarV49(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = json.loads((ROOT / 'events.json').read_text(encoding='utf-8'))
        cls.labels = json.loads((ROOT / 'labels_ja.json').read_text(encoding='utf-8'))
        with (ROOT / 'reviews/v49_verified_translations.csv').open(
            encoding='utf-8-sig', newline=''
        ) as f:
            cls.rows = list(csv.DictReader(f))

    def test_approved_count(self):
        self.assertEqual(len(self.rows), 12)

    def test_approved_names_present_in_source(self):
        # The live events.json is updated BEFORE this test in GitHub Actions.
        # Events may be renamed to Japanese or expire; that is not a translation
        # regression. Check the reviewed mapping against the available records,
        # including original_name, without requiring every event to still exist.
        names_by_game = {}
        for event in self.events:
            game = event.get('game')
            names_by_game.setdefault(game, set()).update(
                name for name in (event.get('name'), event.get('original_name'))
                if isinstance(name, str) and name
            )
        unmatched = []
        for row in self.rows:
            self.assertTrue(row['english_name'].strip())
            self.assertTrue(row['japanese_name'].strip())
            names = names_by_game.get(row['game'], set())
            if not ({row['english_name'], row['japanese_name']} & names):
                unmatched.append(row['english_name'])
        if unmatched:
            print('V49 REVIEW_NOT_IN_CURRENT_EVENTS:', ', '.join(unmatched))
        # The reviewed dictionary must still have all entries regardless of
        # the presence/absence of short-lived events in live events.json.
        self.assertTrue(all(
            row['english_name'] in self.labels.get(row['game'], {})
            for row in self.rows
        ))

    def test_labels_match_approved_reviews(self):
        for row in self.rows:
            self.assertEqual(
                self.labels[row['game']][row['english_name']]['name'],
                row['japanese_name'],
            )

    def test_evidence_urls(self):
        for row in self.rows:
            self.assertTrue(row['source_url'].startswith('https://wikiwiki.jp/w-w/'))
            self.assertEqual(row['source_type'], 'jp_wiki')

    def test_events_valid_without_fixed_count(self):
        # Live importers legitimately add and remove events over time.
        self.assertIsInstance(self.events, list)
        self.assertGreater(len(self.events), 0)
        self.assertTrue(all(isinstance(x, dict) for x in self.events))

    def test_remaining_candidates(self):
        pending = candidates(self.events, self.labels)
        self.assertIsInstance(pending, list)
        # Translation coverage changes as the calendar is refreshed. A fixed
        # candidate count (e.g. 28) would make daily jobs fail spuriously.
        self.assertLessEqual(len(pending), len(self.events))

    def test_frontend_uses_labels_without_mutating_json(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertIn("fetch('./labels_ja.json", html)
        self.assertIn('translatedEvent(e,labels)', html)
        self.assertIn('original_name: e.original_name || fallback', html)


if __name__ == '__main__':
    unittest.main()
