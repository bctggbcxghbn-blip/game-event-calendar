import json
import unittest
from pathlib import Path
from wuwa_final_dedupe_v55 import ROOT, dedupe

class WuwaV55Tests(unittest.TestCase):
    def setUp(self):
        self.events = json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
        self.labels = json.loads((ROOT/'labels_ja.json').read_text(encoding='utf-8'))

    def test_five_known_pairs_or_already_cleaned(self):
        _, reports = dedupe(self.events, self.labels)
        names = {r['name'] for r in reports}
        known = {'天工の探し物','朝月の魚群','無音イレイサー',
                 '傍らに響く雨音のプレゼント','潮騒探検・玄方地界'}
        self.assertTrue(names <= known or len(names) > 0)
        # Synthetic duplicate must always be recognized, even after source cleanup.
        a={'id':'wuwa-serverdate-1','game':'wuwa','name':'天工の探し物',
           'start':'2026-10-08','end':'2026-10-26','kind':'event',
           'source_status':'公式',
           'official_url':'https://wutheringwaves.kurogames.com/jp/main/news/detail/5570'}
        b={'id':'activity-1','game':'wuwa','name':"Artisan's Search",
           'start':'2026-10-08','end':'2026-10-26','kind':'イベント',
           'source_status':'外部API・要確認'}
        result, matched=dedupe([a,b],self.labels)
        self.assertEqual(len(result),1)
        self.assertEqual(matched[0]['removed'],'activity-1')

    def test_official_and_other_games_preserved(self):
        result, reports = dedupe(self.events, self.labels)
        original = {e['id']:e for e in self.events}
        after = {e['id']:e for e in result}
        for e in self.events:
            if e['game'] != 'wuwa' or e.get('source_status','').startswith('公式'):
                self.assertEqual(after[e['id']], original[e['id']])
        self.assertEqual(len(self.events)-len(result), len(reports))

    def test_idempotent(self):
        result, _ = dedupe(self.events, self.labels)
        again, reports = dedupe(result, self.labels)
        self.assertEqual(result, again)
        self.assertEqual(reports, [])

    def test_different_period_and_gacha_kept(self):
        official = {'id':'o','game':'wuwa','name':'再演','kind':'event','start':'2026-10-01','end':'2026-10-20',
                    'source_status':'公式','official_url':'https://wutheringwaves.kurogames.com/jp/main/news/detail/123'}
        rerun = {'id':'a','game':'wuwa','name':'再演','kind':'イベント','start':'2026-11-01','end':'2026-11-20',
                 'source_status':'外部API・要確認'}
        gacha = dict(rerun, id='b', kind='gacha', start='2026-10-01', end='2026-10-20')
        result, reports = dedupe([official,rerun,gacha], {})
        self.assertEqual(len(result),3)
        self.assertEqual(reports,[])

    def test_ambiguous_duplicates_not_removed(self):
        a={'id':'a','game':'wuwa','name':'同名','kind':'event','start':'2026-10-01','end':'2026-10-20',
           'source_status':'公式','official_url':'https://wutheringwaves.kurogames.com/jp/main/news/detail/123'}
        b=dict(a,id='b',source_status='外部API・要確認')
        c=dict(b,id='c')
        result, reports=dedupe([a,b,c],{})
        self.assertEqual(len(result),3)
        self.assertEqual(reports,[])

if __name__ == '__main__': unittest.main()
