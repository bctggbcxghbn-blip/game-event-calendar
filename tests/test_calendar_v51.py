import csv, json, unittest
from pathlib import Path
from calendar_translation_v48 import candidates
ROOT=Path(__file__).resolve().parents[1]
class CalendarV51(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.labels=json.loads((ROOT/'labels_ja.json').read_text(encoding='utf-8'))
  cls.events=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
  with (ROOT/'reviews/v51_verified_translations.csv').open(encoding='utf-8-sig',newline='') as f:cls.rows=list(csv.DictReader(f))
 def test_eight_distinct_records(self):
  self.assertEqual(len(self.rows),8)
  self.assertEqual(len({(r['game'],r['english_name']) for r in self.rows}),8)
 def test_approved_labels_match(self):
  for r in self.rows:self.assertEqual(self.labels[r['game']][r['english_name']]['name'],r['japanese_name'])
 def test_evidence_sources(self):
  for r in self.rows:
   self.assertTrue(r['source_url'].startswith('https://'))
   self.assertIn(r['source_type'],{'jp_wiki','official'})
  self.assertEqual(sum(r['source_type']=='official' for r in self.rows),1)
 def test_source_names_present(self):
  existing={(e.get('game'),e.get('name')) for e in self.events}
  self.assertTrue({(r['game'],r['english_name']) for r in self.rows}<=existing)
 def test_translation_candidates_exclude_approved(self):
  pending={(r['game'],r['english_name']) for r in candidates(self.events,self.labels)}
  self.assertFalse(pending & {(r['game'],r['english_name']) for r in self.rows})
 def test_data_valid_not_fixed_count(self):
  self.assertIsInstance(self.events,list)
  self.assertTrue(self.events)
  self.assertTrue(all(isinstance(e,dict) for e in self.events))
 def test_frontend_translation_lookup(self):
  html=(ROOT/'index.html').read_text(encoding='utf-8')
  self.assertIn("fetch('./labels_ja.json",html)
  self.assertIn('translatedEvent(e,labels)',html)
if __name__=='__main__':unittest.main()
