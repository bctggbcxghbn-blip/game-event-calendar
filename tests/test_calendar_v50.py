import csv, json, unittest
from pathlib import Path
from calendar_translation_v48 import candidates
ROOT=Path(__file__).resolve().parents[1]
class CalendarV50(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.labels=json.loads((ROOT/'labels_ja.json').read_text(encoding='utf-8'))
  cls.events=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
  with (ROOT/'reviews/v50_verified_translations.csv').open(encoding='utf-8-sig',newline='') as f:cls.rows=list(csv.DictReader(f))
 def test_translation_records(self):
  self.assertEqual(len(self.rows),10)
  self.assertEqual(len({(r['game'],r['english_name']) for r in self.rows}),len(self.rows))
 def test_approved_labels_match(self):
  for r in self.rows:self.assertEqual(self.labels[r['game']][r['english_name']]['name'],r['japanese_name'])
 def test_evidence_urls(self):
  for r in self.rows:
   self.assertTrue(r['source_url'].startswith('https://wikiwiki.jp/'))
   self.assertEqual(r['source_type'],'jp_wiki')
 def test_only_expected_games(self):
  self.assertEqual({r['game'] for r in self.rows},{'genshin','zzz'})
 def test_calendar_data_valid_not_fixed_count(self):
  self.assertTrue(isinstance(self.events,list) and len(self.events)>0)
  self.assertTrue(all(isinstance(e,dict) for e in self.events))
 def test_candidates_exclude_verified_names(self):
  pending={(r['game'],r['english_name']) for r in candidates(self.events,self.labels)}
  self.assertFalse(pending & {(r['game'],r['english_name']) for r in self.rows})
 def test_frontend_uses_translation_map(self):
  html=(ROOT/'index.html').read_text(encoding='utf-8')
  self.assertIn("fetch('./labels_ja.json",html)
  self.assertIn('translatedEvent(e,labels)',html)
if __name__=='__main__':unittest.main()
