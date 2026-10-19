import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"games"/"nte"))
from nte_discover_v60 import discover, build_report, KNOWN

class TestV60(unittest.TestCase):
    def setUp(self):
        self.html = f"""<a href="/jp/article/news/gamenews/20261020/265000.html">Ver.1.5「新章」アップデートのお知らせ</a>
        <a href="{KNOWN}">Ver.1.4「名もなき祈歌」アップデートのお知らせ</a>
        <a href="https://evil.example/jp/article/news/gamenews/20261020/999.html">Ver.9.9 アップデート</a>
        <a href="/jp/article/news/gamenews/20261021/265001.html">サーバーメンテナンス</a>"""
    def test_discovery(self):
        self.assertEqual(len(discover(self.html)), 2)
    def test_known_filtered(self):
        self.assertEqual(len(build_report(self.html, {KNOWN})["candidates"]), 1)
    def test_no_auto_import(self):
        self.assertEqual(build_report(self.html, {KNOWN})["auto_imported"], 0)
    def test_external_ignored(self):
        self.assertTrue(all("evil" not in x["url"] for x in discover(self.html)))
    def test_empty_safe(self):
        self.assertEqual(discover(""), [])
    def test_relative_and_absolute(self):
        self.assertTrue(all(x["url"].startswith("https://nte.perfectworld.com/") for x in discover(self.html)))
if __name__ == "__main__":
    unittest.main()
