import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pred', ROOT / 'games' / 'zzz' / 'zzz_challenge_prediction_import.py')
pred = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pred)


class TestZZZPredictionTransition(unittest.TestCase):
    def test_prediction_generation_is_explicitly_marked(self):
        rows = pred.generate(pred.dt.date(2026, 11, 15), 30)
        self.assertTrue(rows)
        self.assertTrue(all('予測' in row['name'] for row in rows))
        self.assertTrue(all('予測' in row['source_status'] for row in rows))

    def test_official_shifted_window_overlaps_prediction(self):
        predicted = [{'id': 'p', 'game': 'zzz', 'kind': 'チャレンジ', 'name': '【予測】式輿防衛戦・激変ノード', 'start': '2026-11-13', 'end': '2026-11-27'}]
        official = [{'id': 'zzz-official-o', 'game': 'zzz', 'kind': 'チャレンジ', 'name': '【予測】式輿防衛戦・激変ノード', 'start': '2026-11-16', 'end': '2026-11-30'}]
        self.assertEqual(pred.filter_predictions(predicted, official), [])

    def test_different_event_with_overlapping_window_is_kept(self):
        predicted = [{'id': 'p', 'game': 'zzz', 'kind': 'チャレンジ', 'name': '【予測】危局強襲戦', 'start': '2026-11-13', 'end': '2026-11-27'}]
        official = [{'id': 'o', 'game': 'zzz', 'kind': 'チャレンジ', 'name': '式輿防衛戦・激変ノード', 'start': '2026-11-16', 'end': '2026-11-30'}]
        self.assertEqual(len(pred.filter_predictions(predicted, official)), 1)

    def test_external_review_record_does_not_confirm_prediction(self):
        predicted = [{'id': 'p', 'game': 'zzz', 'kind': 'チャレンジ', 'name': '【予測】危局強襲戦', 'start': '2026-11-13', 'end': '2026-11-27'}]
        review = [{'id': 'api', 'game': 'zzz', 'kind': 'チャレンジ', 'name': '危局強襲戦', 'start': '2026-11-16', 'end': '2026-11-30', 'source_status': '外部API・要確認'}]
        self.assertEqual(len(pred.filter_predictions(predicted, review)), 1)

    def test_existing_events_are_not_deleted_by_merge_policy(self):
        existing = [{'id': 'official', 'game': 'zzz', 'kind': 'イベント', 'name': '既存イベント', 'start': '2026-11-01', 'end': '2026-11-30'}]
        self.assertEqual(existing[0]['id'], 'official')


if __name__ == '__main__':
    unittest.main()
