import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"games"/"nte"))
from nte_article_preview_v61 import extract

class V61Tests(unittest.TestCase):
    def setUp(self):
        self.html="""<html><script>イベント 偽情報</script><h2>プカ遊園祭イベント</h2>
        <p>開催期間：2026年9月30日 ～ 2026年11月11日 06:59（日本時間）</p>
        <h3>限定キャラピックアップ</h3><p>10月21日 06:59まで</p></html>"""
    def test_event(self):
        self.assertTrue(any(x["kind"]=="event_candidate" for x in extract(self.html)["candidates"]))
    def test_gacha(self):
        self.assertTrue(any(x["kind"]=="gacha_candidate" for x in extract(self.html)["candidates"]))
    def test_dates_are_evidence_only(self):
        self.assertTrue(all("start" not in x and "end" not in x for x in extract(self.html)["candidates"]))
    def test_no_auto_import(self):
        self.assertEqual(extract(self.html)["auto_imported"],0)
    def test_script_ignored(self):
        self.assertFalse(any("偽情報" in x["source_text"] for x in extract(self.html)["candidates"]))
    def test_empty(self):
        self.assertEqual(extract("")["candidate_count"],0)
    def test_invalid_date(self):
        self.assertFalse(extract("<p>イベント 2026年2月30日</p>")["candidates"][0]["nearby_dates"])
if __name__=="__main__":
    unittest.main()
