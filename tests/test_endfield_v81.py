import unittest
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('v81',Path(__file__).resolve().parents[1]/'games/endfield/diagnose_v81.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestV81(unittest.TestCase):
    def test_context(self):
        self.assertEqual(m.contexts('abc/api/bulletinxyz',radius=3)[0]['snippet'],'abc/api/bulletinxyz')
    def test_no_context(self):
        self.assertEqual(m.contexts('unrelated'),[])
    def test_json_metadata(self):
        v=m.summarize_api({'status':200,'text':'{"data":[1,2],"ok":true}'})
        self.assertEqual(v['list_lengths']['data'],2)
        self.assertNotIn('text',v)
if __name__=='__main__':unittest.main()
