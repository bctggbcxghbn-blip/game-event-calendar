import importlib.util
import pathlib
import unittest

P = pathlib.Path(__file__).resolve().parents[1] / 'games/wuwa/wuwa_auto_runner_v23.py'
spec = importlib.util.spec_from_file_location('wuwa_v47', P)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestV47(unittest.TestCase):
    def test_only_v22_429_is_skippable(self):
        msg = 'ERROR: extraction failed, no changes: HTTP Error 429: Too Many Requests'
        self.assertTrue(mod.is_safe_challenge_rate_limit('wuwa_challenge_import_v22.py', 1, msg))
        self.assertFalse(mod.is_safe_challenge_rate_limit('wuwa_safe_import_v14.py', 1, msg))
    def test_other_errors_are_fatal(self):
        self.assertFalse(mod.is_safe_challenge_rate_limit('wuwa_challenge_import_v22.py', 1, 'ERROR: extraction failed, no changes: HTTP Error 500'))
        self.assertFalse(mod.is_safe_challenge_rate_limit('wuwa_challenge_import_v22.py', 1, 'HTTP Error 429'))
        self.assertFalse(mod.is_safe_challenge_rate_limit('wuwa_challenge_import_v22.py', 0, 'ERROR: extraction failed, no changes: HTTP Error 429'))
    def test_runner_retains_rollback_guard(self):
        src = P.read_text()
        self.assertIn('EVENTS.read_bytes() != before_step', src)
        self.assertIn('shutil.copy2(backup, EVENTS)', src)
        self.assertIn("current[:len(original)] != original", src)

if __name__ == '__main__': unittest.main()
