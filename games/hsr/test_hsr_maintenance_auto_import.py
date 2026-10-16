#!/usr/bin/env python3
"""Offline tests for hsr_maintenance_auto_import.py; never touches real events.json."""
import contextlib
import datetime as dt
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hsr_maintenance_auto_import as importer

JST = dt.timezone(dt.timedelta(hours=9))
NOW = dt.datetime(2026, 10, 16, 12, 0, tzinfo=JST)


def sample_record(pid='999001', start='2026-11-10'):
    return {
        'id': f'hsr-maintenance-official-{pid}',
        'game': 'hsr',
        'name': 'Ver.4.7 アップデートメンテナンス（終了予定）',
        'start': start,
        'end': start,
        'start_time': '07:00',
        'end_time': '12:00',
        'time_zone': 'Asia/Tokyo',
        'kind': 'メンテナンス',
        'source_status': '公式記事・終了時刻は約5時間後の予定',
        'official_url': f'https://www.hoyolab.com/article/{pid}',
        'url': f'https://www.hoyolab.com/article/{pid}',
    }


class AutoImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.events_path = Path(self.tmp.name) / 'events.json'
        self.write([])

    def write(self, entries):
        self.events_path.write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')

    def read(self):
        return json.loads(self.events_path.read_text(encoding='utf-8'))

    def run_import(self, apply=False, entries=None, records=None):
        if entries is not None:
            self.write(entries)
        if records is None:
            records = [('999001', 'Version 4.7 Update and Maintenance Notice')]
        def candidate(pid, title, now):
            return sample_record(pid), None
        with patch.object(importer, 'EVENTS', self.events_path), \
             patch.object(importer, 'discover', return_value=iter(records)), \
             patch.object(importer, 'candidate', side_effect=candidate), \
             patch.object(importer.dt, 'datetime') as mock_datetime, \
             patch('sys.argv', ['hsr_maintenance_auto_import.py'] + (['--apply'] if apply else [])), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            mock_datetime.now.return_value = NOW
            importer.main()
        return output.getvalue()

    def test_preview_does_not_write(self):
        before = self.events_path.read_bytes()
        log = self.run_import()
        self.assertIn('PREVIEW: 1', log)
        self.assertEqual(self.events_path.read_bytes(), before)

    def test_apply_adds_one_event(self):
        log = self.run_import(apply=True)
        self.assertIn('ADDED: 1', log)
        self.assertEqual(self.read(), [sample_record()])

    def test_repeated_apply_is_idempotent(self):
        self.run_import(apply=True)
        log = self.run_import(apply=True)
        self.assertIn('ADDED: 0', log)
        self.assertEqual(len(self.read()), 1)

    def test_reviewed_date_not_overwritten(self):
        reviewed = {'id': 'hsr-maintenance-manual', 'game': 'hsr',
                    'kind': 'メンテナンス', 'start': '2026-11-10', 'name': 'Reviewed'}
        log = self.run_import(apply=True, entries=[reviewed])
        self.assertIn('already recorded', log)
        self.assertEqual(self.read(), [reviewed])

    def test_unparseable_article_is_skipped(self):
        with patch.object(importer, 'EVENTS', self.events_path), \
             patch.object(importer, 'discover', return_value=iter([('999001', 'Maintenance Notice')])), \
             patch.object(importer, 'candidate', return_value=(None, 'No explicit maintenance start')), \
             patch('sys.argv', ['script', '--apply']), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            importer.main()
        self.assertIn('ADDED: 0', output.getvalue())
        self.assertEqual(self.read(), [])

    def test_candidate_rejects_past_and_distant_dates(self):
        def parse(text):
            start = dt.datetime(2026, 8, 26, 7, tzinfo=JST)
            return (start, start + dt.timedelta(hours=5), 5), None
        with patch.object(importer, 'get_json', return_value={}), \
             patch.object(importer, 'content_text', return_value='text'), \
             patch.object(importer, 'parse_window', side_effect=parse):
            result, reason = importer.candidate('999001', 'Version 4.7 Maintenance Notice', NOW)
        self.assertIsNone(result)
        self.assertIn('120-day', reason)


if __name__ == '__main__':
    unittest.main(verbosity=2)
