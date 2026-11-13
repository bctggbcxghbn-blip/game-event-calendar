import json, tempfile, unittest
from pathlib import Path
from tools.endfield_v93_end_audit import audit
class TestV93(unittest.TestCase):
    def test_read_only_and_no_guessed_ends(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); (root/'games/endfield').mkdir(parents=True)
            (root/'games/endfield/v89_verified_candidates.json').write_text(json.dumps({'events':[{'id':'e1','title':'A','start_date':'2026-11-05','end_date':None,'end_condition':'next update','source_cid':'1'}]}))
            events=root/'events.json';events.write_text(json.dumps([{'id':'e1','game':'endfield','end':None}]))
            before=events.read_bytes();r=audit(root)
            self.assertEqual(r['unconfirmed'],1);self.assertEqual(r['registered'],1)
            self.assertEqual(events.read_bytes(),before)
    def test_missing_candidate(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); (root/'games/endfield').mkdir(parents=True)
            (root/'games/endfield/v89_verified_candidates.json').write_text(json.dumps({'events':[{'id':'e1','title':'A','start_date':'2026-11-05'}]}))
            (root/'events.json').write_text('[]')
            self.assertEqual(audit(root)['items'][0]['review_status'],'not_registered')
