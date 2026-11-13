import importlib.util
import unittest
from pathlib import Path

PATH = Path('games/wuwa/wuwa_wiki_runner_v46.py')
spec = importlib.util.spec_from_file_location('wuwa_v46', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestV49(unittest.TestCase):
    def report(self, rc=3):
        return {'status':'failed','exit_code':rc,'rate_limits':3,'errors':['STOP INDEX HTTP_429']}

    def test_index_429(self):
        self.assertTrue(module.safe_rate_limit_abort(3,self.report(), 'RATE_LIMIT HTTP_429\nSTOP_INDEX_ERROR HTTP_429 NO_WRITES'))

    def test_version_429(self):
        self.assertTrue(module.safe_rate_limit_abort(4,self.report(4), 'RATE_LIMIT HTTP_429\nSTOP_VERSION_ERROR HTTP_429 NO_WRITES'))

    def test_other_error_still_fails(self):
        self.assertFalse(module.safe_rate_limit_abort(3,self.report(), 'STOP_INDEX_ERROR HTTP_429'))
        self.assertFalse(module.safe_rate_limit_abort(3,{'status':'failed','exit_code':3,'rate_limits':0,'errors':['other']},'STOP_INDEX_ERROR HTTP_429 NO_WRITES'))

if __name__=='__main__': unittest.main()
