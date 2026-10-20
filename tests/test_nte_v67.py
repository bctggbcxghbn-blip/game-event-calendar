import unittest
from games.nte.nte_v67_add_hunter import import_event, EVENT_ID

class TestNTEV67(unittest.TestCase):
    def test_add_once(self):
        events, changed = import_event([])
        self.assertTrue(changed)
        self.assertEqual(events[0]["id"], EVENT_ID)
        again, changed = import_event(events)
        self.assertFalse(changed)
        self.assertEqual(again, events)

    def test_name_dedupe(self):
        events = [{"game": "nte", "name": "ハンター褒章"}]
        self.assertFalse(import_event(events)[1])

    def test_reject_wrong_format(self):
        with self.assertRaises(ValueError):
            import_event({})
