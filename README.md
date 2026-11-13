# Endfield V95 — 公式記事の再取得（読み取り専用）

最新版リポジトリZIPから作成した差分パッチです。フォルダ構造を維持してGitHubへアップロードしてください。

- `.github/workflows/update.yml` — V51鳴潮修正・V94・他ゲームの既存ステップを維持し、V95の3ステップを追加
- `tools/endfield_v95_live_review.py` — 公式APIの候補記事を実行時に取得し、日付表現を調査用に記録
- `tests/test_endfield_v95.py` — オフラインテスト

**終了日を自動確定しません。** 記事にある日付がイベント終了日とは限りません。通信に失敗した場合もレポートに明示します。`events.json` やデザインは変更しません。

Actionsを実行後、Artifact `endfield-v95-official-live-review` をダウンロードして共有してください。
