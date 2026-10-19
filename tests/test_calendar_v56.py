import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from calendar_update_audit_v56 import audit

class CalendarV56(unittest.TestCase):
    def setUp(self):
        self.base=[{'id':'a','game':'wuwa','name':'Event A','kind':'event','start':'2026-10-19','end':'2026-10-25'}]
        self.today=dt.date(2026,10,19)
    def test_valid(self):
        r=audit(self.base,today=self.today);self.assertEqual(r['status'],'ok');self.assertEqual(r['active_today'],1)
    def test_invalid_dates(self):
        x=[dict(self.base[0],end='2026-02-30')];self.assertEqual(audit(x,today=self.today)['status'],'error')
    def test_reversed_dates(self):
        x=[dict(self.base[0],end='2026-10-01')];self.assertEqual(audit(x,today=self.today)['status'],'error')
    def test_duplicate_ids(self):
        self.assertEqual(audit(self.base*2,today=self.today)['status'],'error')
    def test_possible_duplicate_only_warning(self):
        x=self.base+[dict(self.base[0],id='b')];r=audit(x,today=self.today);self.assertEqual(r['status'],'review');self.assertEqual(len(r['warnings']),1)
    def test_distinct_period_not_duplicate(self):
        x=self.base+[dict(self.base[0],id='b',start='2026-11-01',end='2026-11-15')];self.assertEqual(audit(x,today=self.today)['status'],'ok')
    def test_changes(self):
        x=[dict(self.base[0],name='New name'),dict(self.base[0],id='b')];r=audit(x,self.base,self.today);self.assertEqual(r['changes']['added'],1);self.assertEqual(r['changes']['modified'],1)
    def test_read_only(self):
        import copy
        x=copy.deepcopy(self.base);audit(x,self.base,self.today);self.assertEqual(x,self.base)
if __name__=='__main__':unittest.main()
