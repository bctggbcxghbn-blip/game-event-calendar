import unittest
from games.endfield.diagnose_v83 import module_contexts,script_urls

class V83Tests(unittest.TestCase):
    def test_module_declaration(self):
        self.assertEqual(len(module_contexts('x,{56006:(e,t,r)=>{let x={cms:{host:"https://example.com",appCode:"abc"}}}}')),1)
    def test_reference_not_declaration(self):
        self.assertEqual(module_contexts('r(56006).a.cms.host'),[])
    def test_scripts(self):
        self.assertEqual(len(script_urls('<script src="https://web-static.hg-cdn.com/a.js"></script><script src="https://evil.com/b.js"></script>')),1)
if __name__=='__main__':unittest.main()
