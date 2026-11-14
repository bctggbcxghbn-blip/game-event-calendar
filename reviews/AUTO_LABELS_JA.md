# 根拠付き日本語名称の自動反映

`tools/auto_labels_ja.py` は、確認済みの英語名・日本語名の組だけを
`labels_ja.json` に追加します。機械翻訳や、開催期間だけによる照合はしません。
`events.json`、日時、分類、HTML、CSSは変更しません。

## 根拠として使うもの

- `reviews/*_verified_translations.csv` に記録済みの確認済み対応表。
  ゲーム、英語名、日本語名、根拠URL、情報元の種類、確認日が必要です。
- 公式・日本語Wiki由来と記録されたイベントで、同じレコードに
  `original_name` と日本語の `name`、対応ゲームの許可済み情報元URLがあるもの。
- 既に確認された同一タイトルに、明確な告知用表記
  `"タイトル" Event Details` が付いたもの。

公式サイトと日本語Wikiを対象とします。以前に確認済みのコミュニティ多言語表
（`localization_index`）も、対応ゲームの許可済みドメインに限定して再利用します。
保存済みの確認記録を再利用する処理であり、根拠ページの現在の内容を毎回
取得して再検証する処理ではありません。

未確認の名称、別ゲーム、似た名前、根拠不足、複数の日本語名がある候補は保留します。
既存の日本語名は上書きしません。新しいイベントが自動的にすべて日本語化される
わけではありません。新規の確認済み対応表や、取得元の明示的な名称ペアが増えると、
次回の自動更新で利用できます。

## 実行

```powershell
python tools/auto_labels_ja.py
python tools/auto_labels_ja.py --apply
```

通常実行はプレビューです。`--apply` のときだけ名称辞書と根拠履歴を更新します。
結果は `.reports/auto-labels-ja/report.json`、追加根拠は
`reviews/auto_labels_ja_evidence.json` に保存します。繰り返し実行しても重複追加しません。

GitHub Actionsでは、全ゲームの取り込み後、最終品質監査の前に適用します。
確認待ち・衝突した名称はレポートに残し、正常なイベント更新を止めません。
名称辞書と根拠履歴はイベント更新と一緒にコミットします。

テストは `python -m unittest discover -s tests -p 'test_auto_labels_ja.py' -v`。
全体検証は `tools/verify_calendar.py` で行います。既存名称の上書きは拒否し、
新規名称は確認済み根拠から再現できる追加だけを認めます。
