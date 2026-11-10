import unittest, ast, pathlib, types
P = pathlib.Path(__file__).resolve().parents[1] / 'games/wuwa/wuwa_dynamic_gacha_import_v29.py'
tree = ast.parse(P.read_text(encoding='utf-8'))
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate')
namespace = {}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(P), 'exec'), namespace)
mod = types.SimpleNamespace(validate=namespace['validate'])

class TestV48(unittest.TestCase):
    def setUp(self):
        self.marker = {'id':'endfield-v92-test','game':'endfield','kind':'イベント','name':'test','start':'2026-11-05','end':None,'source_status':'公式開始日確認済み・終了日未定','end_note':'次回メンテナンス前','official_url':'https://endfield.gryphline.com/ja-jp/news/1234'}
    def test_v92_marker_allowed(self):
        mod.validate([self.marker], [])
    def test_other_game_missing_end_rejected(self):
        bad = dict(self.marker, game='wuwa')
        with self.assertRaisesRegex(ValueError,'invalid event schema'): mod.validate([bad], [])
    def test_unverified_endfield_missing_end_rejected(self):
        bad = dict(self.marker, source_status='unknown')
        with self.assertRaisesRegex(ValueError,'invalid event schema'): mod.validate([bad], [])
    def test_valid_ordinary_event(self):
        mod.validate([dict(self.marker,game='wuwa',end='2026-12-01')], [])
    def test_existing_event_immutability(self):
        with self.assertRaisesRegex(ValueError,'existing event records changed'): mod.validate([dict(self.marker,name='changed')],[self.marker])
    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError,'missing or duplicate IDs'): mod.validate([self.marker,self.marker], [])

if __name__ == '__main__': unittest.main()
