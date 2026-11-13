import json
import tempfile
import unittest
from pathlib import Path
from tools.endfield_v95_live_review import inspect, detail_url

class V95Tests(unittest.TestCase):
    def test_read_only_and_no_inferred_end_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'games/endfield').mkdir(parents=True)
            (root/'games/endfield/v89_verified_candidates.json').write_text(json.dumps({'events':[{'id':'e1','title':'イベント','source_cid':'9560','end_condition':'メンテナンス前'}]}),encoding='utf-8')
            events='[{"id":"e1","game":"endfield","end":null}]'
            (root/'events.json').write_text(events,encoding='utf-8')
            report=inspect(root,lambda url:{'data':{'body':'開催期間：2026年12月03日 04:00'}})
            self.assertEqual(report['pending'],1)
            self.assertEqual(report['items'][0]['calendar_end'],None)
            self.assertEqual((root/'events.json').read_text(encoding='utf-8'),events)
            self.assertTrue(report['articles']['9560']['date_mentions'])
    def test_failed_fetch_is_reported_not_silenced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'games/endfield').mkdir(parents=True)
            (root/'games/endfield/v89_verified_candidates.json').write_text(json.dumps({'events':[{'id':'e','title':'t','source_cid':'2652'}]}),encoding='utf-8')
            (root/'events.json').write_text('[]',encoding='utf-8')
            def fail(url): raise RuntimeError('429')
            r=inspect(root,fail)
            self.assertEqual(r['articles']['2652']['status'],'fetch_failed')
            self.assertEqual(r['pending'],1)

if __name__=='__main__': unittest.main()
