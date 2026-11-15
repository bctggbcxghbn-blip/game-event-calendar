import importlib.util, json, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('nte_v60',ROOT/'games/nte/nte_official_v60.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class TestNTEV60Official(unittest.TestCase):
    def test_discovers_latest_version(self):
        html='<a href="/jp/article/news/gamenews/20261109/264951.html">Ver.1.5「新章」アップデートのお知らせ</a><a href="/jp/article/news/gamenews/20260929/264412.html">Ver.1.4アップデート</a>'
        self.assertEqual(m.discover_versions(html)[0]['version'],'1.5')
    def test_extracts_only_explicit_period(self):
        text='<p>イベント「シティ物流」</p><p>イベント期間:11月11日 - 12月23日06:59 (JST)</p><p>開放時間:Ver.1.5アップデート後</p>'
        rows=m.dated_events(text,'https://nte.perfectworld.com/jp/article/news/gamenews/20261109/264951.html','1.5',2026)
        self.assertEqual(len(rows),1); self.assertEqual(rows[0]['name'],'シティ物流'); self.assertEqual(rows[0]['start'],'2026-11-11'); self.assertEqual(rows[0]['end'],'2026-12-23')
    def test_merge_deduplicates_stable_ids(self):
        row={'id':'x','game':'nte','name':'確認済み','start':'2026-11-11','end':'2026-12-23'}
        self.assertEqual(len(m.merge([row],[row])),1)

if __name__=='__main__': unittest.main()
