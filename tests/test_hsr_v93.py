import importlib.util, json, pathlib, tempfile, unittest
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'games/hsr/hsr_gacha_dedupe.py'
spec = importlib.util.spec_from_file_location('hsr_dedupe_v93', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Tests(unittest.TestCase):
    def run_case(self, rows, should_fail=False):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / 'events.json'
            original = json.dumps(rows, ensure_ascii=False)
            path.write_text(original)
            with patch.object(mod, 'PATH', path), patch('sys.argv', ['x', '--apply']):
                if should_fail:
                    with self.assertRaises(RuntimeError): mod.main()
                else: mod.main()
            return json.loads(path.read_text())
    def official(self, name, ident):
        return dict(id=ident, game='hsr', name=name, start='2026-09-28', end='2026-11-10', end_time='16:00', start_label='アップデート後', official_url=mod.OFFICIAL)
    def test_already_deduplicated(self):
        rows=[self.official(name, ids[0]) for name, ids in mod.PAIRS.items()]
        self.assertEqual(self.run_case(rows), rows)
    def test_missing_both_is_noop(self):
        self.assertEqual(self.run_case([]), [])
    def test_stale_without_official_refused(self):
        name, ids=next(iter(mod.PAIRS.items()))
        self.run_case([dict(id=ids[1], game='hsr', name=name)], True)
    def test_mismatched_official_refused(self):
        name, ids=next(iter(mod.PAIRS.items()))
        row=self.official(name, ids[0]);row['end']='2027-01-01'
        self.run_case([row], True)
    def test_actual_pair_removes_only_stale(self):
        name, ids=next(iter(mod.PAIRS.items()))
        stale=dict(id=ids[1], game='hsr', name=name, start='2026-10-21', end='2026-11-11')
        rows=[self.official(name, ids[0]),stale,dict(id='other',game='genshin')]
        result=self.run_case(rows)
        self.assertEqual([r['id'] for r in result],[ids[0],'other'])

if __name__=='__main__': unittest.main()
