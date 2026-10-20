import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'games/nte'))
from nte_import_v71 import run
BASE={'id':'nte-new','game':'nte','name':'新イベント','kind':'イベント','start':'2026-11-12','end':'2026-11-20','official_url':'https://nte.perfectworld.com/jp/article/test','source_status':'公式確認済み','reviewed':True}
class TestV71(unittest.TestCase):
 def test_approved_add(self):
  add,r=run([], [BASE], {'articles':[{}]});self.assertEqual(len(add),1);self.assertNotIn('reviewed',add[0])
 def test_dedupe(self):
  add,r=run([{k:v for k,v in BASE.items() if k!='reviewed'}],[BASE],{});self.assertEqual(add,[])
 def test_reject_unreviewed(self):
  add,r=run([],[dict(BASE,reviewed=False)],{});self.assertEqual(add,[]);self.assertEqual(len(r['rejected']),1)
 def test_ignore_raw_discovery(self):
  add,r=run([],[],{'articles':[{'candidates':[{'name':'test'}]}]});self.assertEqual(add,[])
if __name__=='__main__':unittest.main()
