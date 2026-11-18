import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = (ROOT / 'index.html').read_text(encoding='utf-8')


class CalendarStage2UiTests(unittest.TestCase):
    def test_bulk_visibility_and_reset_controls_exist(self):
        for control in ('showAll', 'hideAll', 'resetPrefs'):
            self.assertIn(control, HTML)
        self.assertIn('function setAll(enabled)', HTML)
        self.assertIn('function resetPrefs()', HTML)

    def test_visibility_settings_are_persisted(self):
        self.assertIn("localStorage.setItem('timelinePrefs'", HTML)
        self.assertIn("localStorage.removeItem('timelinePrefs')", HTML)
        self.assertIn('games:[...enabledGames]', HTML)
        self.assertIn('types:[...enabledTypes]', HTML)

    def test_unknown_versions_are_explicit(self):
        self.assertIn('const VERSION=', HTML)
        self.assertIn('Ver.未確認', HTML)

    def test_stage2_visual_rules_preserve_game_color_and_thicken_bars(self):
        self.assertIn('--game-color:${G[e.game][1]}', HTML)
        self.assertIn(".bar{border-width:3px", HTML)


if __name__ == '__main__':
    unittest.main()
