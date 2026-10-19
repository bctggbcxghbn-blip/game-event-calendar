import datetime as dt
import unittest
from calendar_update_monitor_v57 import assess

D=dt.date(2026,10,19)
def ev(game='wuwa',end='2026-11-11',i=0):return {'id':str(i),'game':game,'name':'Test','start':'2026-10-01','end':end}

class MonitorV57(unittest.TestCase):
    def test_healthy(self):
        data=[ev(i=i) for i in range(20)]
        self.assertEqual(assess(data,data,D,0)['status'],'ok')
    def test_total_drop_warning(self):
        self.assertIn('LARGE_TOTAL_DROP',[w['code'] for w in assess([ev(i=i) for i in range(10)],[ev(i=i) for i in range(30)],D)['warnings']])
    def test_game_drop_warning(self):
        prev=[ev('wuwa',i=i) for i in range(10)]+[ev('hsr',i=20+i) for i in range(10)]
        cur=[ev('wuwa',i=0)]+[ev('hsr',i=20+i) for i in range(10)]
        self.assertIn('LARGE_GAME_DROP',[w['code'] for w in assess(cur,prev,D)['warnings']])
    def test_stale_warning(self):
        data=[ev(i=i) for i in range(20)]
        self.assertIn('NO_DATA_CHANGE_7_DAYS',[w['code'] for w in assess(data,data,D,7)['warnings']])
    def test_no_baseline_not_stale(self):
        self.assertEqual(assess([ev(i=i) for i in range(20)],None,D,None)['status'],'ok')
    def test_past_events_warning(self):
        self.assertIn('NO_CURRENT_OR_FUTURE_EVENTS',[w['code'] for w in assess([ev(end='2026-10-01',i=i) for i in range(3)],None,D)['warnings']])
    def test_warning_not_critical(self):
        r=assess([ev(i=i) for i in range(1)],[ev(i=i) for i in range(30)],D)
        self.assertEqual(r['status'],'review');self.assertEqual(r['critical'],[])
    def test_invalid_root(self):
        self.assertEqual(assess({},None,D)['status'],'error')

if __name__=='__main__':unittest.main()
