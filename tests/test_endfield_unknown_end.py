"""Offline regression tests; only temporary calendar copies may be written."""
import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import update_events
from event_dates import valid_event_dates
from calendar_quality_v47 import analyze
from calendar_update_audit_v56 import audit


class UnknownEndTests(unittest.TestCase):
    def setUp(self):
        self.marker = dict(id='endfield-test', game='endfield', name='確認済みイベント',
                           kind='イベント', start='2026-11-05', end=None,
                           source_status='公式開始日確認済み・終了日未定',
                           end_note='次回メンテナンス前',
                           official_url='https://endfield.gryphline.com/ja-jp/news/1234')

    def assert_contract(self, event, expected):
        before = copy.deepcopy(event)
        self.assertEqual(valid_event_dates(event), expected)
        self.assertEqual(update_events.valid(event), expected)
        self.assertEqual(not any(i['type'] == 'invalid_dates' for i in analyze([event])['issues']), expected)
        report = audit([event], today=dt.date(2026, 11, 5))
        self.assertEqual(not any(i['type'] == 'invalid_dates' for i in report['critical']), expected)
        self.assertEqual(event, before)

    def test_verified_marker(self):
        self.assert_contract(self.marker, True)
        report = audit([self.marker], today=dt.date(2026, 11, 5))
        self.assertEqual(report['active_today'], 0)
        self.assertEqual(report['critical'], [])
        self.assertTrue(any(w['type'] == 'unknown_end' for w in report['warnings']))

    def test_v46_accepts_marker_and_confirmed_end(self):
        from test_calendar_v46 import CalendarV46
        case = CalendarV46()
        case.events = [self.marker, dict(self.marker, id='confirmed', end='2026-11-10')]
        case.test_data_structure()
        case.test_valid_calendar_dates()

    def test_reject_invalid_markers(self):
        changes = [dict(end=''), dict(end=3), dict(start='2026-02-30'),
                   dict(start='20261105'), dict(source_status='unknown'),
                   dict(end_note=''), dict(name=''), dict(kind=''),
                   dict(official_url='https://endfield.gryphline.com.evil/ja-jp/news/1234'),
                   dict(official_url='https://endfield.gryphline.com/ja-jp/news/'),
                   dict(official_url='http://endfield.gryphline.com/ja-jp/news/1234')]
        for change in changes:
            with self.subTest(change=change):
                self.assert_contract(dict(self.marker, **change), False)
        missing = dict(self.marker)
        del missing['end']
        self.assert_contract(missing, False)

    def test_other_games_keep_end_required(self):
        for game in sorted(update_events.GAMES - {'endfield'}):
            with self.subTest(game=game):
                self.assert_contract(dict(self.marker, game=game), False)
                self.assert_contract(dict(self.marker, game=game, end='2026-11-10'), True)

    def test_confirmed_end_is_allowed_and_reversed_end_rejected(self):
        self.assert_contract(dict(self.marker, end='2026-11-10'), True)
        self.assert_contract(dict(self.marker, end='2026-11-04'), False)

    def test_temporary_merge_retains_then_updates_same_id(self):
        ordinary = dict(id='hsr-test', game='hsr', name='通常', kind='イベント',
                        start='2026-11-01', end='2026-11-10')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'events.json'
            path.write_text(json.dumps([ordinary, self.marker]), encoding='utf-8')
            (root / 'sources.json').write_text('{"feeds": []}', encoding='utf-8')
            with patch.object(update_events, 'ROOT', root):
                update_events.main()
                first = path.read_bytes()
                update_events.main()
                self.assertEqual(first, path.read_bytes())
                self.assertCountEqual(json.loads(first), [ordinary, self.marker])
                confirmed = dict(self.marker, end='2026-11-10')
                (root / 'sources.json').write_text('{"feeds": ["https://example.com/feed"]}', encoding='utf-8')
                with patch.object(update_events, 'download', return_value=json.dumps([confirmed]).encode()):
                    update_events.main()
                self.assertCountEqual(json.loads(path.read_bytes()), [ordinary, confirmed])

    def test_v92_to_update_to_audits(self):
        spec = importlib.util.spec_from_file_location('endfield_v92', ROOT / 'games/endfield/import_v92.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'games/endfield'
            folder.mkdir(parents=True)
            shutil.copyfile(ROOT / 'games/endfield/v89_verified_candidates.json', folder / 'v89_verified_candidates.json')
            (root / 'events.json').write_text('[]', encoding='utf-8')
            (root / 'sources.json').write_text('{"feeds": []}', encoding='utf-8')
            self.assertGreater(module.apply(root), 0)
            original = json.loads((root / 'events.json').read_bytes())
            with patch.object(update_events, 'ROOT', root):
                update_events.main()
            result = json.loads((root / 'events.json').read_bytes())
            self.assertCountEqual(original, result)
            self.assertTrue(all(e['end'] is None for e in result))
            self.assertFalse(audit(result)['critical'])
            self.assertFalse(any(i['level'] == 'error' for i in analyze(result)['issues']))

    def test_javascript_start_markers_and_ordinary_ranges(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node unavailable; run JavaScript assertions with a JS runtime')
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        script = html.split('<script>')[1].split('let detailItems=')[0]
        assertions = '''
start='2026-11-05';
for(const kind of ['イベント','新キャラガチャ','武器・装備ガチャ']){
  const e={id:kind,game:'endfield',name:kind,kind,start,end:null};
  const lanes=displayItems([e]);
  if(lanes.length!==1||lanes[0].segments[0].displayEnd!==start||e.end!==null)throw Error(kind);
  if(!detailText(lanes[0].segments[0]).includes('未定（開始日のみ表示）'))throw Error('detail');
  start='2026-11-06';if(displayItems([e]).length)throw Error('ongoing');start=e.start;
}
for(const game of ['genshin','wuwa','hsr','zzz','nte','arknights','endfield']){
  for(const kind of ['イベント','ガチャ']){
    const e={id:game,game,name:game,kind,start,end:'2026-11-10'};
    if(displayItems([e])[0].segments[0].displayEnd!==e.end)throw Error('ordinary');
  }
}
'''
        bootstrap = "global.document={getElementById:()=>({})};global.localStorage={getItem:()=>null};\n"
        subprocess.run([node, '-e', bootstrap + script + assertions], check=True, capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()
