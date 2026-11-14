import unittest
from tools.endfield_v97_period_review import classify

class PeriodTests(unittest.TestCase):
    def test_other_event_date_is_not_accepted(self):
        x={"id":"a","title":"A","matches":[{"alias":"A","context":"A·開催期間：バージョン開始後～バージョンアップメンテナンス前·説明：その他イベント·開催期間：2026/11/05 12:00～2026/11/19 11:59"}]}
        y=classify(x)
        self.assertEqual(y["verified_end"],None)
        self.assertEqual(y["periods"][0]["status"],"conditional_end")
    def test_count_condition(self):
        x={"id":"b","title":"B","matches":[{"alias":"B","context":"B·開催期間：開始後、特別スカウトが3回開催されると終了·説明：内容"}]}
        self.assertEqual(classify(x)["periods"][0]["status"],"conditional_end")
    def test_no_matches(self):
        self.assertEqual(classify({"id":"x","title":"X","matches":[]})["periods"],[])
if __name__ == "__main__": unittest.main()
