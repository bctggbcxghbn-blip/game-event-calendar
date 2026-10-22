import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "games" / "endfield" / "diagnose_v86.py"
spec = importlib.util.spec_from_file_location("diagnose_v86", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class V86Tests(unittest.TestCase):
    def test_host_is_official_news_api(self):
        self.assertEqual(module.HOST, "https://web-news.gryphline.com/api/bulletin")
    def test_fetch_encodes_tabs_as_repeated_array_parameters(self):
        pairs = [("tabs[]", "1"), ("tabs[]", "2")]
        from urllib.parse import urlencode
        encoded = urlencode(pairs)
        self.assertIn("tabs%5B%5D=1", encoded)
        self.assertIn("tabs%5B%5D=2", encoded)
    def test_report_path_is_versioned(self):
        self.assertIn("endfield-v86", module.OUT)

if __name__ == "__main__":
    unittest.main()
