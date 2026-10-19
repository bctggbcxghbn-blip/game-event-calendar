import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import calendar_summary_v58 as v58


class SummaryV58(unittest.TestCase):
    def setUp(self):
        self.q = {'status':'ok','count':93,'active_today':57,'critical':[],'warnings':[],
                  'counts_by_game':{'wuwa':31,'zzz':27},'change_comparison_available':True,
                  'changes':{'added':1,'removed':2,'modified':0}}
        self.m = {'status':'review','total':93,'critical':[],
                  'warnings':[{'code':'NO_DATA_CHANGE_7_DAYS'}]}

    def test_summary_counts(self):
        s = v58.build(self.q, self.m)
        self.assertIn('93', s)
        self.assertIn('| wuwa | 31 |', s)

    def test_changes(self):
        self.assertIn('Added: **1**', v58.build(self.q, self.m))

    def test_warnings_visible(self):
        self.assertIn('NO_DATA_CHANGE_7_DAYS', v58.build(self.q, self.m))

    def test_missing_reports_graceful(self):
        self.assertIn('unavailable', v58.build(None, None))

    def test_escape_markdown(self):
        self.assertEqual(v58.safe('a|b\nc'), 'a\\|b c')

    def test_does_not_write_source(self):
        self.assertIn('never modifies events.json', v58.build(self.q, self.m))


if __name__ == '__main__':
    unittest.main()
