import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "games" / "endfield" / "v89_verified_candidates.json"

class TestEndfieldV89(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))

    def test_review_only_and_source(self):
        self.assertEqual(self.data["version"], 89)
        self.assertEqual(self.data["mode"], "review_only")
        self.assertEqual(self.data["source"]["cid"], "9560")
        self.assertTrue(self.data["source"]["source_verified"])

    def test_seven_candidates(self):
        self.assertEqual(len(self.data["events"]), 7)
        self.assertEqual(len({e["id"] for e in self.data["events"]}), 7)

    def test_no_guessed_end_dates(self):
        for event in self.data["events"]:
            self.assertEqual(event["status"], "review_required")
            self.assertIsNone(event["end_date"])
            self.assertTrue(event["end_condition"])
