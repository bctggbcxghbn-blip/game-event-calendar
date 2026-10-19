# V47 データ品質監査（表示デザイン変更なし）

- `tests/calendar_quality_v47.py` は `events.json` と `labels_ja.json` を読み取り、`.reports/calendar-v47/report.json` に監査結果を書き出す。
- 英語名の未翻訳候補、ガチャ新規・復刻の未確認候補、同名同期間、ID重複、日付異常を報告する。
- **翻訳を推測して適用しない**。ガチャの新規・復刻も勝手に判定しない。
- エラー（重複ID・不正日付）のみ終了コード1でワークフローを停止。要確認項目は報告のみ。
- `index.html`、`events.json`、`labels_ja.json`、取得スクリプトは変更しない。
- GitHub ActionsのArtifacts `calendar-quality-v47` に監査JSONを14日間保存。
- 実際の翻訳反映や取得漏れの改善は、確認済みの公式・日本語Wikiの対応表が必要。
