import unittest
from calendar_translation_v48 import candidates,apply_review

class TranslationV48(unittest.TestCase):
 def setUp(self):
  self.events=[{'game':'wuwa','name':'Back to Solaris'},{'game':'wuwa','name':'Back to Solaris'},{'game':'hsr','name':'巡星の礼'}]
  self.labels={'wuwa':{}}
 def test_candidates_deduplicated(self):self.assertEqual(len(candidates(self.events,self.labels)),1)
 def test_known_labels_excluded(self):self.assertEqual(candidates(self.events,{'wuwa':{'Back to Solaris':{'name':'確認済み'}}}),[])
 def test_valid_review(self):
  row={'game':'wuwa','english_name':'Back to Solaris','japanese_name':'ソラリスへの帰還','source_url':'https://example.com/source','source_type':'official','reviewed_on':'2026-10-19'}
  result,added=apply_review([row],self.events,self.labels)
  self.assertEqual(len(added),1);self.assertEqual(result['wuwa']['Back to Solaris']['name'],'ソラリスへの帰還')
 def test_missing_evidence_rejected(self):
  row={'game':'wuwa','english_name':'Back to Solaris','japanese_name':'ソラリスへの帰還','source_url':'','source_type':'official','reviewed_on':'2026-10-19'}
  with self.assertRaises(ValueError):apply_review([row],self.events,self.labels)
 def test_unknown_name_rejected(self):
  row={'game':'wuwa','english_name':'Unknown','japanese_name':'仮','source_url':'https://example.com','source_type':'official','reviewed_on':'2026-10-19'}
  with self.assertRaises(ValueError):apply_review([row],self.events,self.labels)
 def test_original_unchanged(self):
  before=repr(self.events),repr(self.labels);candidates(self.events,self.labels);self.assertEqual(before,(repr(self.events),repr(self.labels)))
 def test_conflicting_translation_rejected(self):
  row={'game':'wuwa','english_name':'Back to Solaris','japanese_name':'別の翻訳','source_url':'https://example.com','source_type':'official','reviewed_on':'2026-10-19'}
  with self.assertRaises(ValueError):apply_review([row],self.events,{'wuwa':{'Back to Solaris':{'name':'確認済み'}}})
