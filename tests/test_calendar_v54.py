import json, re, shutil, subprocess, unittest
from pathlib import Path
from calendar_dedupe_v54 import audit
ROOT=Path(__file__).resolve().parents[1]
class CalendarV54(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.events=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
  cls.labels=json.loads((ROOT/'labels_ja.json').read_text(encoding='utf-8'))
  cls.html=(ROOT/'index.html').read_text(encoding='utf-8')
 def test_known_wuwa_duplicates_resolved_or_detectable(self):
  # Import-side cleanup V55 may already have removed the original duplicates.
  duplicates=audit(self.events,self.labels)
  names={key[1] for key,ids in duplicates if key[0]=='wuwa'}
  self.assertEqual(len(names),len(set(names)))
  sample=[
   {'id':'a','game':'wuwa','name':"Artisan's Search",'start':'2026-10-08','end':'2026-10-26','kind':'イベント'},
   {'id':'b','game':'wuwa','name':'天工の探し物','start':'2026-10-08','end':'2026-10-26','kind':'event'}]
  found=audit(sample,self.labels)
  self.assertEqual(len(found),1)
  self.assertEqual(found[0][0][1],'天工の探し物')
 def test_read_only(self):
  before=json.dumps(self.events,ensure_ascii=False)
  audit(self.events,self.labels)
  self.assertEqual(json.dumps(self.events,ensure_ascii=False),before)
 def test_browser_dedupe(self):
  node=shutil.which('node')
  if not node:self.skipTest('Node unavailable')
  match=re.search(r'function dedupeDisplayEvents\(items\)\{.*?\n\}',self.html,re.S)
  self.assertIsNotNone(match)
  script="""const type=e=>e.kind==='gacha'?'gacha':'event';
"""+match.group(0)+"""
const a={id:'activity-1',game:'wuwa',name:'天工の探し物',start:'2026-10-08',end:'2026-10-26',kind:'イベント'};
const b={...a,id:'wuwa-serverdate-1',kind:'event'};
const c={...b,id:'different-period',end:'2026-10-27'};
const d={...b,id:'different-game',game:'zzz'};
const e={...b,id:'different-type',kind:'gacha'};
const result=dedupeDisplayEvents([a,b,c,d,e]);
if(result.length!==4)process.exit(1);
if(result[0].id!=='wuwa-serverdate-1')process.exit(2);
if(dedupeDisplayEvents(result).length!==4)process.exit(3);
"""
  result=subprocess.run([node,'-e',script],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
 def test_frontend_applies_dedupe_after_translation(self):
  self.assertIn('dedupeDisplayEvents([...map.values()].map(e=>translatedEvent(e,labels)))',self.html)
if __name__=='__main__':unittest.main()
