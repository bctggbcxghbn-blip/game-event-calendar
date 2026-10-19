# V48: 英語イベント名の照合候補（デザイン変更なし）

- 既存の `events.json` と `labels_ja.json` を参照し、未翻訳の英語名をCSVに出力します。
- GitHub ActionsのArtifact `calendar-translation-v48` から `translation_candidates.csv` を取得できます。
- 公式・日本語Wikiの表記を人が確認して、CSVの `japanese_name`, `source_url`, `source_type` (`official` / `jp_wiki`), `reviewed_on` (`YYYY-MM-DD`) を記入します。
- **注意**: URLは入力形式だけを検査します。掲載内容の自動検証ではありません。照合は必ず人が行ってください。
- 確認済みCSVを適用する場合: `python tests/calendar_translation_v48.py --apply-reviewed path/to/reviewed.csv`。
- 既存翻訳と矛盾する内容や根拠URLのない翻訳は拒否します。`events.json` は変更しません。
- 自動更新ワークフローではCSVの生成のみを行い、未確認の翻訳は自動反映しません。
- V47で挙がった40件は監査候補の件数です。V48は既存辞書の適用状況によって候補数が変わる場合があります。
