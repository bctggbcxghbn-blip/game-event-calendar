import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "games" / "endfield" / "diagnose_v85.py"
spec = importlib.util.spec_from_file_location("diagnose_v85", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class EndfieldV85Tests(unittest.TestCase):
    def test_endpoint_and_read_only_mode(self):
        self.assertEqual(mod.HOST, "https://web-news.gryphline.com")
        self.assertEqual(mod.APP_CODE, "arknights_endfield_official")

    def test_array_encoding_cases_exist(self):
        names = [name for name, _ in mod.CASES]
        self.assertIn("tabs_brackets_zero", names)
        self.assertIn("tabs_index_zero", names)
        self.assertIn("tabs_repeated_zero_one", names)
        self.assertIn("tabs_json_array", names)

    def test_probe_count_and_query_encoding(self):
        self.assertGreaterEqual(len(mod.CASES), 6)
        query = __import__("urllib.parse", fromlist=["urlencode"]).urlencode([("tabs[]", "0")])
        self.assertIn("tabs%5B%5D=0", query)

if __name__ == "__main__":
    unittest.main()
