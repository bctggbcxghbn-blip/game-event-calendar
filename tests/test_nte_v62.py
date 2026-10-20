import sys,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'games/nte'))
from nte_review_v62 import compare
class TestV62(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.raw=json.loads((ROOT/'tests/fixtures/nte_v61_candidates.json').read_text())
  cls.out=compare(cls.raw)
 def test_70_candidates(self):self.assertEqual(self.out['source_candidate_count'],70)
 def test_14_registered(self):self.assertEqual(self.out['registered_v59_count'],14)
 def test_no_writes(self):self.assertEqual(self.out['auto_imported'],0)
 def test_all_periods_unverified(self):self.assertTrue(all(not x['period_verified'] for x in self.out['registered_items']))
 def test_noise_remains_unmatched(self):self.assertTrue(any('不具合を修正' in x['source_text'] for x in self.out['unmatched_candidates']))
 def test_bad_input(self):
  with self.assertRaises(ValueError):compare({'status':'error'})
 def test_unique_ids(self):self.assertEqual(len({x['id'] for x in self.out['registered_items']}),14)
if __name__=='__main__':unittest.main()
