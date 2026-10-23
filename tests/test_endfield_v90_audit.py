import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "endfield_v90_repo_audit.py"
SPEC = importlib.util.spec_from_file_location("endfield_v90_repo_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class TestEndfieldV90Audit(unittest.TestCase):
    def test_shape_dict(self):
        self.assertEqual(MODULE.summarize_shape({"events": [{"title": "x"}]}), {"events": {"type": "list", "length": 1, "sample_shape": {"title": "str"}}})

    def test_shape_empty_list(self):
        self.assertEqual(MODULE.summarize_shape([]), {"type": "list", "length": 0, "sample_shape": None})

    def test_load_json_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text("{bad", encoding="utf-8")
            data, err = MODULE.load_json(p)
            self.assertIsNone(data)
            self.assertTrue(err)

if __name__ == "__main__":
    unittest.main()
