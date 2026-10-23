import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "games" / "endfield" / "diagnose_v88.py"
spec = importlib.util.spec_from_file_location("diagnose_v88", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class V88Tests(unittest.TestCase):
    def test_official_endpoint_and_app_code(self):
        self.assertEqual(mod.HOST, "https://web-news.gryphline.com/api/bulletin")
        self.assertEqual(mod.APP_CODE, "arknights_endfield_official")

    def test_known_article_detail_url(self):
        url = mod.detail_url("2652")
        self.assertIn("/api/bulletin/2652?", url)
        self.assertIn("lang=ja-jp", url)
        self.assertIn("arknights_endfield_official", url)

    def test_candidate_scoring(self):
        item = {"title": "「玉書・申請」期間限定ピックアップについて", "brief": "開催期間：特別スカウトが3回開催されると終了"}
        score, hits = mod.score_item(item)
        self.assertGreater(score, 0)
        self.assertIn("玉書", hits)

if __name__ == "__main__":
    unittest.main()
