import unittest
from calendar_quality_v47 import analyze

class CalendarQualityV47(unittest.TestCase):
    def item(self, **overrides):
        d = dict(id='a', game='wuwa', name='Back to Solaris', kind='event', start='2026-10-01', end='2026-10-10')
        d.update(overrides)
        return d
    def test_untranslated_english_flagged(self):
        self.assertEqual(analyze([self.item()])['issue_counts']['english_name_untranslated'], 1)
    def test_verified_translation_not_flagged(self):
        self.assertNotIn('english_name_untranslated', analyze([self.item()], {'wuwa': {'Back to Solaris': {'name': '確認済みの訳'}}})['issue_counts'])
    def test_no_source_mutation(self):
        x = [self.item()]; before = repr(x); analyze(x); self.assertEqual(repr(x), before)
    def test_duplicate_id_error(self):
        self.assertEqual(analyze([self.item(), self.item(name='別イベント')])['issue_counts']['duplicate_or_missing_id'], 1)
    def test_bad_date_error(self):
        self.assertEqual(analyze([self.item(end='2026-09-01')])['issue_counts']['invalid_dates'], 1)
    def test_gacha_unknown_is_informational(self):
        issues = analyze([self.item(name='リンネー', kind='gacha')])['issues']
        self.assertTrue(any(i['level']=='info' for i in issues))
    def test_gacha_known_not_flagged(self):
        issues = analyze([self.item(name='リンネー', kind='gacha', is_rerun=False)])['issues']
        self.assertFalse(any(i['type']=='gacha_release_status_unverified' for i in issues))

if __name__ == '__main__': unittest.main()
