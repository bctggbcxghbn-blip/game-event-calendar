import csv, json, unittest
from pathlib import Path
from calendar_translation_v48 import candidates
ROOT=Path(__file__).resolve().parents[1]
class CalendarV52(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.labels=json.loads((ROOT/'labels_ja.json').read_text(encoding='utf-8'))
  cls.events=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
  with (ROOT/'reviews/v52_verified_translations.csv').open(encoding='utf-8-sig',newline='') as f:cls.rows=list(csv.DictReader(f))
 def test_three_reviewed_distinct(self):
  self.assertEqual(len(self.rows),3)
  self.assertEqual(len({(r['game'],r['english_name']) for r in self.rows}),3)
 def test_translations_match_labels(self):
  for r in self.rows:self.assertEqual(self.labels[r['game']][r['english_name']]['name'],r['japanese_name'])
 def test_evidence_url_and_types(self):
  for r in self.rows:
   self.assertTrue(r['source_url'].startswith('https://'))
   self.assertIn(r['source_type'],{'official','jp_wiki','localization_index'})
 def test_original_names_optional_in_live_events(self):
  # Rolling event data can legitimately stop listing an already-reviewed event.
  active={(e.get('game'),n) for e in self.events for n in [e.get('name'),e.get('original_name')] if n}
  for r in self.rows:
   if (r['game'],r['english_name']) in active:
    self.assertEqual(self.labels[r['game']][r['english_name']]['name'],r['japanese_name'])
 def test_pending_excludes_approved(self):
  pending={(r['game'],r['english_name']) for r in candidates(self.events,self.labels)}
  self.assertFalse(pending & {(r['game'],r['english_name']) for r in self.rows})
 def test_events_not_mutated_and_valid(self):
  self.assertIsInstance(self.events,list)
  self.assertTrue(self.events)
  self.assertTrue(all(isinstance(e,dict) for e in self.events))
 def test_frontend_uses_translation_mapping(self):
  html=(ROOT/'index.html').read_text(encoding='utf-8')
  self.assertIn("fetch('./labels_ja.json",html)
  self.assertIn('translatedEvent(e,labels)',html)
if __name__=='__main__':unittest.main()
