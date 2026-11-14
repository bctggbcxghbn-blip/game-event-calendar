"""Evidence-only auto labels: no inferred translations or changes to event data."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import auto_labels_ja as auto


class AutoLabelsTests(unittest.TestCase):
    def setUp(self):
        self.event = dict(id='event', game='wuwa', name='Back to Solaris', start='2026-11-01', end='2026-11-10')
        self.pair = dict(game='wuwa', english_name='Back to Solaris', japanese_name='ソラリスへの復帰招待',
                         source_url='https://wikiwiki.jp/w-w/Ver3.7', source_type='jp_wiki', reviewed_on='2026-10-19')

    def test_verified_exact_pair(self):
        events, labels = [self.event], {}
        before = copy.deepcopy((events, labels))
        updated, report = auto.reconcile(events, labels, [self.pair])
        self.assertEqual(updated['wuwa']['Back to Solaris']['name'], self.pair['japanese_name'])
        self.assertEqual(len(report['applied']), 1)
        self.assertEqual((events, labels), before)

    def test_wrong_game_and_similar_names_not_matched(self):
        for event in (dict(self.event, game='genshin'), dict(self.event, name='Back to Solaris II')):
            with self.subTest(event=event):
                updated, report = auto.reconcile([event], {}, [self.pair])
                self.assertEqual(updated, {})
                self.assertEqual(len(report['pending']), 1)

    def test_existing_translation_never_overwritten(self):
        labels = {'wuwa': {'Back to Solaris': {'name': '既存名称', 'kind': 'イベント'}}}
        result, report = auto.reconcile([self.event], labels, [self.pair])
        self.assertEqual(result, labels)
        self.assertEqual(len(report['conflicts']), 1)

    def test_conflicting_sources_held(self):
        result, report = auto.reconcile([self.event], {}, [self.pair, dict(self.pair, japanese_name='別名称')])
        self.assertEqual(result, {})
        self.assertEqual(len(report['conflicts']), 1)

    def test_missing_or_invalid_evidence_rejected(self):
        for change in ({'source_url': ''}, {'source_url': 'https://wikiwiki.jp.evil/w-w/Ver3.7'},
                       {'source_url': 'https://wikiwiki.jp/genshinwiki/events'},
                       {'source_url': 'http://wikiwiki.jp/w-w/Ver3.7'}, {'reviewed_on': 'bad'},
                       {'reviewed_on': '2099-01-01'}, {'japanese_name': 'Guessed Name'}):
            with self.subTest(change=change):
                result, report = auto.reconcile([self.event], {}, [dict(self.pair, **change)])
                self.assertEqual(result, {})
                self.assertEqual(len(report['rejected']), 1)

    def test_verified_bilingual_official_record(self):
        e = dict(self.event, original_name=self.event['name'], name='ソラリスへの復帰招待',
                 source_status='公式確認済み', official_url='https://wutheringwaves.kurogames.com/jp/main/news/detail/123')
        result, report = auto.reconcile([e], {}, [])
        self.assertIn('Back to Solaris', result['wuwa'])
        self.assertEqual(report['applied'][0]['sources'][0]['evidence_event_id'], 'event')
        e['source_status'] = '外部API・要確認'
        result, _ = auto.reconcile([e], {}, [])
        self.assertEqual(result, {})

    def test_explicit_wrapper_only(self):
        pair = dict(self.pair, game='zzz', english_name='Advanced Bounty: Area Patrol', japanese_name='先遣賞金-区域防衛',
                    source_type='localization_index', source_url='https://zenless-zone-zero.fandom.com/wiki/Advanced_Bounty%3A_Area_Patrol')
        event = dict(self.event, game='zzz', name='"Advanced Bounty: Area Patrol" Event Details')
        result, report = auto.reconcile([event], {}, [pair])
        self.assertEqual(result['zzz'][event['name']]['name'], '先遣賞金-区域防衛')
        self.assertEqual(report['applied'][0]['matching'], 'explicit_event_details_wrapper')
        result, _ = auto.reconcile([dict(event, name='Advanced Bounty: Area Patrol Event Details Extra')], {}, [pair])
        self.assertEqual(result, {})

    def test_apply_is_idempotent_and_event_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'reviews').mkdir()
            (root / 'events.json').write_text(json.dumps([self.event]), encoding='utf-8')
            (root / 'labels_ja.json').write_text('{}', encoding='utf-8')
            original = (root / 'events.json').read_bytes()
            with patch.object(auto, 'reviewed_pairs', return_value=[self.pair]), patch.object(sys, 'argv', ['auto', '--root', str(root)]):
                self.assertEqual(auto.main(), 0)
            self.assertEqual((root / 'labels_ja.json').read_bytes(), b'{}')
            for run in range(2):
                with patch.object(auto, 'reviewed_pairs', return_value=[self.pair]), patch.object(sys, 'argv', ['auto', '--root', str(root), '--apply']):
                    self.assertEqual(auto.main(), 0)
                if run == 0:
                    first = (root / 'labels_ja.json').read_bytes()
                else:
                    self.assertEqual(first, (root / 'labels_ja.json').read_bytes())
            self.assertEqual((root / 'events.json').read_bytes(), original)
            history = json.loads((root / 'reviews/auto_labels_ja_evidence.json').read_bytes())
            self.assertEqual(len(history['entries']), 1)

    def test_actions_apply_before_final_audit_and_commit_labels(self):
        workflow = (ROOT / '.github/workflows/update.yml').read_text(encoding='utf-8')
        apply = workflow.index('      - name: Apply verified Japanese labels automatically')
        self.assertGreater(apply, workflow.index('python games/nte/nte_import_v71.py --apply'))
        self.assertLess(apply, workflow.index('      - name: Audit calendar update quality V56'))
        self.assertIn('git add events.json labels_ja.json', workflow)
        self.assertIn('git add reviews/auto_labels_ja_evidence.json', workflow)


if __name__ == '__main__':
    unittest.main()
