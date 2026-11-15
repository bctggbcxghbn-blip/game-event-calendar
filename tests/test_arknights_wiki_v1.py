import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('ak',ROOT/'games/arknights/arknights_wiki_v1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestArknightsWiki(unittest.TestCase):
    def test_extract_dated_row(self):
        html='<table><tr><th>イベント名</th><th>期間</th></tr><tr><td>泡影を穿つ碧雷</td><td>2026/11/16 16:00 〜 11/30 03:59</td></tr></table>'
        r=m.extract(html);self.assertEqual(len(r),1);self.assertEqual(r[0]['start'],'2026-11-16');self.assertEqual(r[0]['end'],'2026-11-30')
    def test_extract_paragraph_event(self):
        html='<p><a>泡影を穿つ碧雷</a><br />(2026/11/16 16:00 〜 11/30 03:59)</p>'
        r=m.extract(html);self.assertEqual(len(r),1);self.assertEqual(r[0]['name'],'泡影を穿つ碧雷')
    def test_ambiguous_period_skipped(self): self.assertEqual(m.extract('<table><tr><td>危機契約#5</td><td>2026年12月上旬</td></tr></table>'),[])
    def test_merge_deduplicates(self):
        x={'id':'x','game':'arknights','name':'A','start':'2026-11-16','end':'2026-11-30'};self.assertEqual(len(m.merge([x],[x])),1)
    def test_jp_cn_sections_are_separated(self):
        html='<h2>開催中のイベント</h2><p>JPイベント<br>(2026/11/16 16:00 〜 11/30 03:59)</p><h2>大陸版の実装順</h2><p>CNイベント<br>(2026/11/20 16:00 〜 12/04 03:59)</p>'
        r=m.extract(html, require_jp_section=True); self.assertEqual([x['name'] for x in r], ['JPイベント'])
    def test_unknown_structure_fails_closed(self):
        self.assertEqual(m.extract('<h2>イベント一覧</h2><p>不明<br>(2026/11/16 16:00 〜 11/30 03:59)</p>', require_jp_section=True), [])
    def test_existing_events_are_retained_when_scope_changes(self):
        existing=[{'id':'old','game':'arknights','name':'時間啊、向前！','start':'2026-11-01','end':'2026-11-22'}]
        incoming=m.extract('<h2>開催予定のイベント</h2><p>泡影を穿つ碧雷<br>(2026/11/16 16:00 〜 11/30 03:59)</p>', require_jp_section=True)
        merged=m.merge(existing,incoming); self.assertEqual({x['id'] for x in merged},{'old',incoming[0]['id']})
if __name__=='__main__':unittest.main()
