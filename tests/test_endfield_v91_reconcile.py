import json, tempfile, unittest
from pathlib import Path
from tools.endfield_v91_reconcile import audit

class TestEndfieldV91(unittest.TestCase):
    def test_candidates_wait_when_end_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"events.json"; p.write_text("[]",encoding="utf-8")
            c=Path(td)/"candidates.json"
            c.write_text(json.dumps({"events":[{"id":"x","title":"イベント","start_date":"2026-11-05","end_date":None,"end_condition":"メンテ前"}]}),encoding="utf-8")
            r=audit(p,c)
            self.assertEqual(r["status_counts"],{"waiting_for_verified_end":1})
    def test_exact_id_detected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"events.json"; p.write_text(json.dumps([{"id":"x","game":"endfield","name":"イベント","start":"2026-11-05","end":"2026-11-06"}]),encoding="utf-8")
            c=Path(td)/"candidates.json"
            c.write_text(json.dumps({"events":[{"id":"x","title":"イベント","start_date":"2026-11-05","end_date":None,"end_condition":"メンテ前"}]}),encoding="utf-8")
            self.assertEqual(audit(p,c)["candidates"][0]["status"],"already_registered_id")
    def test_read_only_report(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"events.json"; p.write_text("[]",encoding="utf-8")
            before=p.read_bytes()
            c=Path(td)/"candidates.json"; c.write_text(json.dumps({"events":[]}),encoding="utf-8")
            audit(p,c)
            self.assertEqual(p.read_bytes(),before)
if __name__ == "__main__": unittest.main()
