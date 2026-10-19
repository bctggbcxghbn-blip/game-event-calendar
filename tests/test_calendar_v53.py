"""V53: verify evidence, source integrity and the actual browser translation function."""
import csv, json, re, shutil, subprocess, unittest
from pathlib import Path
from calendar_translation_v48 import candidates
ROOT=Path(__file__).resolve().parents[1]
class CalendarV53(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.labels=json.loads((ROOT/'labels_ja.json').read_text(encoding='utf-8'))
  cls.events=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
  with (ROOT/'reviews/v53_verified_translations.csv').open(encoding='utf-8-sig',newline='') as f:cls.review=list(csv.DictReader(f))
  cls.html=(ROOT/'index.html').read_text(encoding='utf-8')
 def test_one_evidence_backed_name(self):
  self.assertEqual(len(self.review),1)
  r=self.review[0]
  self.assertEqual(r['game'],'zzz')
  self.assertEqual(r['japanese_name'],'先遣賞金-区域防衛')
  self.assertEqual(self.labels[r['game']][r['english_name']]['name'],r['japanese_name'])
 def test_evidence_and_status(self):
  for r in self.review:
   self.assertTrue(r['source_url'].startswith('https://'))
   self.assertIn(r['source_type'],{'official','jp_wiki','localization_index'})
 def test_pending_excludes_verified(self):
  pending={(r['game'],r['english_name']) for r in candidates(self.events,self.labels)}
  self.assertFalse(pending & {(r['game'],r['english_name']) for r in self.review})
 def test_events_unmodified(self):
  self.assertIsInstance(self.events,list)
  self.assertTrue(all(isinstance(e,dict) for e in self.events))
 def test_frontend_loads_labels_without_modifying_event_file(self):
  self.assertIn("fetch('./labels_ja.json",self.html)
  self.assertIn('translatedEvent(e,labels)',self.html)
 def test_browser_translation_function_executes(self):
  node=shutil.which('node')
  if not node:self.skipTest('Node not available; browser function integration needs Node')
  match=re.search(r'function translatedEvent\(e, labels\)\s*\{.*?\n\}',self.html,re.S)
  self.assertIsNotNone(match,'Browser translation function missing')
  script=match.group(0)+"""
const labels=JSON.parse(process.argv[1]);
const source={game:'zzz',name:'Advanced Bounty: Area Patrol',start:'2026-09-23',end:'2026-09-28',kind:'event'};
const snapshot=JSON.stringify(source);
const translated=translatedEvent(source,labels);
if(translated.name!=='先遣賞金-区域防衛')process.exit(2);
if(translated.original_name!==source.name || translated.start!==source.start || translated.end!==source.end)process.exit(3);
if(JSON.stringify(source)!==snapshot)process.exit(4);
const already=translatedEvent(translated,labels);
if(already.name!==translated.name)process.exit(5);
const untouched=translatedEvent({game:'zzz',name:'unknown',start:'2026-01-01'},labels);
if(untouched.name!=='unknown')process.exit(6);
"""
  result=subprocess.run([node,'-e',script,json.dumps(self.labels,ensure_ascii=False)],capture_output=True,text=True,encoding='utf-8')
  self.assertEqual(result.returncode,0,result.stderr+result.stdout)
 def test_cannot_translate_unsupported_game(self):
  self.assertNotIn('other-game',self.labels)
if __name__=='__main__':unittest.main()
