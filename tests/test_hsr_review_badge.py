import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = (ROOT / 'index.html').read_text(encoding='utf-8')


class HsrReviewBadgeTests(unittest.TestCase):
    def test_badge_is_limited_to_hsr_external_review_records(self):
        self.assertIn("e.game==='hsr'&&e.source_status==='外部API・要確認'", HTML)
        self.assertIn("needsReviewBadge(e)?'<em class=\"review-badge\">要確認</em>':''", HTML)

    def test_badge_keeps_existing_bar_and_filters(self):
        self.assertIn('class="bar segment"', HTML)
        self.assertIn("type(e)==='gacha'", HTML)
        self.assertIn('enabledTypes.has(type(e))', HTML)

    def test_badge_is_compact_and_mobile_safe(self):
        self.assertIn('.review-badge{', HTML)
        self.assertIn('flex-shrink:0', HTML)
        self.assertIn('@media(max-width:700px)', HTML)


if __name__ == '__main__':
    unittest.main()
