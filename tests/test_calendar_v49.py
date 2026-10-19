import csv, json, re, unittest
from pathlib import Path
from calendar_translation_v48 import candidates
ROOT=Path(__file__).resolve().parents[1]
class CalendarV49(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
        cls.labels=json.loads((ROOT/'labels_ja.json').read_text(encoding='utf-8'))
        with (ROOT/'reviews/v49_verified_translations.csv').open(encoding='utf-8-sig',newline='') as f:cls.rows=list(csv.DictReader(f))
    def test_approved_count(self):self.assertEqual(len(self.rows),12)
    def test_approved_names_present_in_source(self):
        names={(x['game'],x['name']) for x in self.events}
        self.assertTrue(all((r['game'],r['english_name']) in names for r in self.rows))
    def test_labels_match_approved_reviews(self):
        for r in self.rows:self.assertEqual(self.labels[r['game']][r['english_name']]['name'],r['japanese_name'])
    def test_evidence_urls(self):
        for r in self.rows:
            self.assertTrue(r['source_url'].startswith('https://wikiwiki.jp/w-w/'))
            self.assertEqual(r['source_type'],'jp_wiki')
    def test_events_unchanged_and_97(self):self.assertEqual(len(self.events),97)
    def test_remaining_candidates(self):self.assertEqual(len(candidates(self.events,self.labels)),28)
    def test_frontend_uses_labels_without_mutating_json(self):
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        self.assertIn("fetch('./labels_ja.json",html)
        self.assertIn('translatedEvent(e,labels)',html)
        self.assertIn('original_name: e.original_name || fallback',html)
if __name__=='__main__':unittest.main()
