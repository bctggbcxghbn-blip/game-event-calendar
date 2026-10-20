import unittest, importlib.util, pathlib
p=pathlib.Path(__file__).resolve().parents[1]/'games/endfield/import_v72.py'
spec=importlib.util.spec_from_file_location('endfield_import',p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class TestMerge(unittest.TestCase):
 def test_add(self):
  merged,added=mod.merge([], [{'id':'a','game':'endfield','name':'A'}]);self.assertEqual(len(added),1)
 def test_idempotent(self):
  item={'id':'a','game':'endfield','name':'A'};merged,added=mod.merge([item],[item]);self.assertEqual(added,[]);self.assertEqual(len(merged),1)
