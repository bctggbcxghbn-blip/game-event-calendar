import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'games'/'endfield'))
from audit_v74 import audit,norm
class TestAudit(unittest.TestCase):
 def test_dedup(self):
  r={'articles':[{'candidate_text':['「百趣演武」 · 開催期間：2026/10/29','「百趣演武」 · 開催期間：2026/10/29']} ]}
  self.assertEqual(audit(r,[])['unique_named_candidates'],1)
 def test_match(self):
  r={'articles':[{'candidate_text':['「百趣演武」 · 開催期間：2026/10/29']}]}
  self.assertEqual(audit(r,[{'game':'endfield','name':'百趣演武','id':'x'}])['possibly_registered'],1)
 def test_other_game_ignored(self):
  r={'articles':[{'candidate_text':['「百趣演武」 · 開催期間：2026/10/29']}]}
  self.assertEqual(audit(r,[{'game':'hsr','name':'百趣演武'}])['needs_review'],1)
if __name__=='__main__':unittest.main()
