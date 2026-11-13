# Endfield V93 — 終了日監査（読み取り専用）

3ファイルを同じ相対パスでリポジトリへ追加・上書きしてください：
- `.github/workflows/update.yml` （V49適用前のアップロードZIPを基に作成。**V49以降の変更がある場合はこのファイルを丸ごと上書きしないこと**）
- `tools/endfield_v93_end_audit.py`
- `tests/test_endfield_v93.py`

**重要**：既存ワークフローを守るため、推奨は新規2ファイルを追加し、`update.yml` には `Test Endfield V93...` から `Upload Endfield V93...` までの3ステップだけを追記することです。挿入場所は `Test Endfield V91 reconciliation (offline)` の直前。

Actions実行後、Artifact `endfield-v93-end-date-audit` を取得してください。
V93は終了日の公式発表を新規に取得するものではありません。未確定日の現状監査のみで、イベントデータを変更しません。
