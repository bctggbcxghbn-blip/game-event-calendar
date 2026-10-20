import unittest
from games.nte.nte_check_v70 import audit, EXPECTED
class TestV70(unittest.TestCase):
    def test_all_present(self):
        data=[{'id':k,'name':v,'game':'nte'} for k,v in EXPECTED.items()]
        self.assertTrue(audit(data)['safe_to_skip'])
    def test_missing(self):
        self.assertFalse(audit([])['safe_to_skip'])
    def test_duplicate(self):
        k,v=next(iter(EXPECTED.items()))
        self.assertEqual(audit([{'id':k,'name':v,'game':'nte'}]*2)['candidates'][0]['status'],'duplicate')
if __name__=='__main__':unittest.main()
