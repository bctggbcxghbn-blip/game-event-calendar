import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('ak',ROOT/'games/arknights/arknights_wiki_v1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestArknightsWiki(unittest.TestCase):
    def test_extract_dated_row(self):
        html='<table><tr><th>イベント名</th><th>期間</th></tr><tr><td>泡影を穿つ碧雷</td><td>2026/11/16 16:00 〜 11/30 03:59</td></tr></table>'
        r=m.extract(html);self.assertEqual(len(r),1);self.assertEqual(r[0]['start'],'2026-11-16');self.assertEqual(r[0]['end'],'2026-11-30')
    def test_ambiguous_period_skipped(self): self.assertEqual(m.extract('<table><tr><td>危機契約#5</td><td>2026年12月上旬</td></tr></table>'),[])
    def test_merge_deduplicates(self):
        x={'id':'x','game':'arknights','name':'A','start':'2026-11-16','end':'2026-11-30'};self.assertEqual(len(m.merge([x],[x])),1)
if __name__=='__main__':unittest.main()
