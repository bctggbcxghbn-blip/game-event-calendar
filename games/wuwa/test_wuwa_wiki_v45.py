#!/usr/bin/env python3
"""V45 offline regression suite for the real V40 importer (no network, no repo writes)."""
import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMPORTER = HERE / 'wuwa_wiki_gacha_import_v40.py'
FUTURE = dt.date.today().year + 3
START, END = f'{FUTURE}-01-10', f'{FUTURE}-01-30'
RERUN_START, RERUN_END = f'{FUTURE}-02-10', f'{FUTURE}-02-28'


def fixture(name='架空の新キャラ', weapon='架空の新武器', start=START, end=END, phase='9.9前'):
    def fmt(s): return s.replace('-', '/')
    return f'''<!doctype html><html><body><table><tr><th>期</th><th>期間</th><th>他</th><th>キャラ</th><th>他</th><th>武器</th></tr>
<tr><td>{phase}</td><td>{fmt(start)} ～ {fmt(end)}</td><td>-</td><td><a href="#">{name}</a></td><td>-</td><td>長刃・{weapon}</td></tr></table></body></html>'''


def run_import(events, html, apply=True):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ev = root / 'events.json'; page = root / 'page.html'
        ev.write_text(json.dumps(events, ensure_ascii=False), encoding='utf-8')
        page.write_text(html, encoding='utf-8')
        args = [sys.executable, str(IMPORTER), '--version', 'Ver9.9', '--events', str(ev), '--html-file', str(page)]
        if apply: args.append('--apply')
        p = subprocess.run(args, capture_output=True, text=True, timeout=15)
        result = json.loads(ev.read_text(encoding='utf-8'))
        return p, result


class WuwaV45Regression(unittest.TestCase):
    def test_new_character_and_weapon(self):
        p, result = run_import([], fixture())
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(len(result), 2)
        self.assertEqual({x['gacha_type'] for x in result}, {'character', 'weapon'})
        self.assertTrue(all(x['time_zone'] == 'unverified_date_only' for x in result))

    def test_repeat_is_idempotent(self):
        p, once = run_import([], fixture())
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        p, twice = run_import(once, fixture())
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(once, twice)
        self.assertIn('APPLY_NO_CHANGES', p.stdout)

    def test_rerun_different_period(self):
        existing = [{'id':'official-old', 'game':'wuwa','kind':'gacha', 'name':'架空の新キャラ', 'gacha_type':'character', 'start':START, 'end':END}]
        p, result = run_import(existing, fixture(start=RERUN_START, end=RERUN_END))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], existing[0])
        self.assertTrue(any(x['name']=='架空の新キャラ' and x['start']==RERUN_START for x in result))

    def test_invalid_reversed_dates_fail_closed(self):
        existing = [{'id':'sentinel', 'game':'genshin','kind':'event','name':'keep'}]
        p, result = run_import(existing, fixture(start=END, end=START))
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(result, existing)
        self.assertIn('STOP:', p.stdout)

    def test_official_record_unchanged(self):
        official = {'id':'official', 'game':'wuwa','kind':'gacha','name':'架空の新キャラ','gacha_type':'character',
                    'start':START+'T11:00:00+09:00','end':END+'T10:59:59+09:00', 'source_status':'official', 'official_url':'https://example.org/official'}
        p, result = run_import([official], fixture())
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(result[0], official)
        self.assertEqual(len(result), 2)  # weapon only

    def test_empty_or_changed_wiki_layout_fail_closed(self):
        existing = [{'id':'sentinel', 'game':'wuwa','kind':'event','name':'keep'}]
        p, result = run_import(existing, '<html><body>Wiki layout changed</body></html>')
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(result, existing)
        self.assertIn('STOP: no parseable', p.stdout)

    def test_dry_run_never_writes(self):
        p, result = run_import([], fixture(), apply=False)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
