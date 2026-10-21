import unittest
from games.endfield.diagnose_v82 import scripts,contexts

class TestV82(unittest.TestCase):
    def test_script_allowlist(self):
        html='<script src="https://web-static.hg-cdn.com/a.js"></script><script src="https://evil.example/b.js"></script>'
        self.assertEqual(scripts(html),['https://web-static.hg-cdn.com/a.js'])
    def test_context(self):
        self.assertTrue(any(x['term']=='appCode' for x in contexts('let x={appCode:"demo"}')))
    def test_context_empty(self):
        self.assertEqual(contexts('no matches'),[])

if __name__=='__main__':unittest.main()
