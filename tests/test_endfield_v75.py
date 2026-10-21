import unittest, tempfile, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'games/endfield'))
from import_v75 import run
class TestV75(unittest.TestCase):
 def test_no_approval_no_change(self):
  with tempfile.TemporaryDirectory() as d:
   e=Path(d)/'events.json';a=Path(d)/'approved.json';e.write_text('[]');a.write_text('{}')
   r=run(e,a,True);self.assertEqual(len(r['waiting_for_verified_end']),7);self.assertEqual(json.loads(e.read_text()),[])
 def test_one_approval(self):
  with tempfile.TemporaryDirectory() as d:
   e=Path(d)/'events.json';a=Path(d)/'approved.json';e.write_text('[]');a.write_text('{"endfield-v75-minho":{"end":"2026-12-01"}}')
   r=run(e,a,True);self.assertEqual(len(r['ready_to_add']),1);self.assertEqual(len(json.loads(e.read_text())),1)
 def test_duplicate_id(self):
  with tempfile.TemporaryDirectory() as d:
   e=Path(d)/'events.json';a=Path(d)/'approved.json';e.write_text('[{"id":"endfield-v75-minho","game":"endfield"}]');a.write_text('{}')
   r=run(e,a,True);self.assertIn('ミンホ「人煙の牽く天河」',r['existing'])
if __name__=='__main__':unittest.main()
