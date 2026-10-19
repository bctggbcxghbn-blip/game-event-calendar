import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'games/nte/nte_official_v59.py'
spec = importlib.util.spec_from_file_location('nte_v59', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class NTEV59Tests(unittest.TestCase):
    def test_all_nte(self):
        self.assertTrue(all(x['game'] == 'nte' for x in m.official_events()))
    def test_unique_ids(self):
        ids = [x['id'] for x in m.official_events()]
        self.assertEqual(len(ids), len(set(ids)))
    def test_idempotent(self):
        self.assertEqual(m.merge(m.merge([])), m.merge([]))
    def test_preserves_other_games(self):
        other = {'id':'other','game':'hsr','start':'2026-09-01'}
        self.assertIn(other, m.merge([other]))
    def test_server_time_not_jst(self):
        item = next(x for x in m.official_events() if x['id'].endswith('pixel'))
        self.assertEqual(item['time_zone'], 'サーバー時間')
    def test_update_relative_uninferred(self):
        item = next(x for x in m.official_events() if x['id'].endswith('kurobane'))
        self.assertNotIn('start_time', item)
    def test_official_source(self):
        self.assertTrue(all(x['official_url'] == m.SOURCE for x in m.official_events()))

if __name__ == '__main__':
    unittest.main()
