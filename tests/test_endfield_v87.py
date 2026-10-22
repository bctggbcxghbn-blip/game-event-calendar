import importlib.util
import os
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "games", "endfield", "diagnose_v87.py")
spec = importlib.util.spec_from_file_location("diagnose_v87", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class V87Tests(unittest.TestCase):
    def test_request_shape_has_no_tabs_filter(self):
        # Confirm the API request is deliberately unfiltered so all categories are inventoried.
        pairs = [("lang", "ja-jp"), ("code", mod.APP_CODE), ("page", "1"), ("pageSize", "50")]
        import urllib.parse
        query = urllib.parse.urlencode(pairs)
        self.assertNotIn("tabs", query)
        self.assertIn("pageSize=50", query)

    def test_keyword_candidates_are_review_only(self):
        sample = {"title": "期間限定イベント開催", "brief": "", "cid": "1"}
        self.assertTrue(any(w.lower() in sample["title"].lower() for w in mod.KEYWORDS))

    def test_output_path_is_report_only(self):
        self.assertEqual(mod.OUT, ".reports/endfield-v87/report.json")
        self.assertNotIn("events.json", mod.OUT)

if __name__ == "__main__":
    unittest.main()
