import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from endfield_v96_event_context import context_matches,inspect

class EndfieldV96(unittest.TestCase):
    def test_title_context(self):
        text='特別スカウト「人煙の牽く天河」2026年11月5日12:00より開始。別イベントは2026年12月3日終了。'
        hits=context_matches(text,'特別スカウト「人煙の牽く天河」',window=38)
        self.assertTrue(hits)
        self.assertTrue(any('2026年11月5日' in d for d in hits[0]['date_mentions_near_title']))
    def test_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'games/endfield';p.mkdir(parents=True)
            entries=[{'id':'a','title':'イベント「独自イベント名」','source_cid':'9560','end_condition':'メンテナンス前'}]
            (p/'v89_verified_candidates.json').write_text(json.dumps({'events':entries}),encoding='utf-8')
            original='[{"id":"a","end":null}]'
            (root/'events.json').write_text(original,encoding='utf-8')
            result=inspect(root,fetch=lambda url:{'data':{'content':'独自イベント名 2026年11月5日開始'}})
            self.assertEqual(result['pending'],1)
            self.assertTrue(result['items'][0]['matches'])
            self.assertEqual((root/'events.json').read_text(encoding='utf-8'),original)

if __name__=='__main__':unittest.main()
