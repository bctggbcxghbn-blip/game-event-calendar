import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'games/hsr/wiki_hsr_gacha.py'
spec = importlib.util.spec_from_file_location('wiki_hsr_gacha_safety', SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def row(kind='character', name='星', start='2026-11-01', end='2026-11-20'):
    return (kind, name, start, end, False, None, None)


class HsrGachaSafetyTests(unittest.TestCase):
    def test_valid_mixed_rows_are_accepted(self):
        rows = [row('character', '星'), row('lightcone', '光'), row('character', '月'), row('lightcone', '夜')]
        mod.validate_candidates(rows, [])

    def test_duplicate_rows_are_rejected(self):
        rows = [row('character', '星'), row('character', '星'), row('lightcone', '光'), row('lightcone', '夜')]
        with self.assertRaisesRegex(ValueError, 'Duplicate warp'):
            mod.validate_candidates(rows, [])

    def test_invalid_period_is_rejected(self):
        rows = [row('character', '星', end='2026-02-30'), row('lightcone', '光'), row('character', '月'), row('lightcone', '夜')]
        with self.assertRaisesRegex(ValueError, 'Invalid warp date'):
            mod.validate_candidates(rows, [])

    def test_large_count_drop_is_rejected_using_existing_rows(self):
        existing = [dict(id=f'wiki-hsr-gacha-{i}', start='2026-01-01', end='2026-01-20') for i in range(8)]
        rows = [row('character', '星'), row('lightcone', '光'), row('character', '月'), row('lightcone', '夜')]
        with self.assertRaisesRegex(ValueError, 'Abnormal warp entry count'):
            mod.validate_candidates(rows, existing)


if __name__ == '__main__':
    unittest.main()
