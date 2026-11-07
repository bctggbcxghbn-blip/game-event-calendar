import unittest
from games.wuwa.wuwa_wiki_runner_v46 import safe_rate_limit_abort

class TestV46(unittest.TestCase):
    def setUp(self):
        self.report = {'status':'failed','exit_code':4,'rate_limits':3,'errors':['STOP_VERSION_ERROR Ver3.7 RuntimeError(HTTP_429) NO_WRITES']}
        self.log = 'RATE_LIMIT HTTP_429\nSTOP_VERSION_ERROR Ver3.7 HTTP_429 NO_WRITES\n'
    def test_safe_429(self):
        self.assertTrue(safe_rate_limit_abort(4,self.report,self.log))
    def test_other_errors_fail(self):
        self.assertFalse(safe_rate_limit_abort(2,self.report,self.log))
        self.assertFalse(safe_rate_limit_abort(4,self.report,'STOP_VERSION_ERROR HTTP_429'))
        self.assertFalse(safe_rate_limit_abort(4,None,self.log))
    def test_success_not_classified(self):
        self.assertFalse(safe_rate_limit_abort(0,self.report,self.log))

if __name__ == '__main__': unittest.main()
