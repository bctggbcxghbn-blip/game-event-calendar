import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/'tools/endfield_v94_official_review.py'
spec=importlib.util.spec_from_file_location('audit94',SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestV94(unittest.TestCase):
    def test_relative_end_not_guessed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'games/endfield').mkdir(parents=True)
            (root/'games/endfield/v89_verified_candidates.json').write_text(json.dumps({'events':[{'id':'a','title':'Example','end_condition':'maintenance'}]}))
            (root/'events.json').write_text(json.dumps([{'id':'a','end':None}]))
            report=mod.build(root)
            self.assertEqual(report['still_undated'],1)
            self.assertIsNone(report['items'][0]['calendar_end'])
    def test_existing_date_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'games/endfield').mkdir(parents=True)
            (root/'games/endfield/v89_verified_candidates.json').write_text(json.dumps({'events':[{'id':'a','title':'Example'}]}))
            (root/'events.json').write_text(json.dumps([{'id':'a','end':'2026-12-01'}]))
            self.assertEqual(mod.build(root)['items'][0]['calendar_end'],'2026-12-01')
if __name__=='__main__': unittest.main()
