# V49 日本語イベント名（表示名のみ）

- 提供されたリポジトリZIPを元にした更新です。V48翻訳候補CSVはZIPに含まれていませんでしたが、同梱の `events.json` と `labels_ja.json` から40件を再生成しました。
- 日本語Wikiで英語名との対応を確認できた鳴潮の12件だけを `labels_ja.json` に登録しています。根拠は `reviews/v49_verified_translations.csv` に記載。
- 既存の `events.json` 97件は変更していません。開催日時、ID、ゲーム、種別を一切変更していません。
- `index.html` は `labels_ja.json` を読み込んで表示時だけ日本語名を優先します。ブラウザ上の見た目・フィルター配置の変更はありません。
- もとの英語名は `original_name` として保持し、辞書の読み込みに失敗した場合は英語のまま表示します。
- 元ファイルの新規イベント取得時も同じ辞書を適用します。将来的に他ゲームでも根拠付き翻訳を追加できます。
- **未確認28件は日本語化していません**。自動的な機械翻訳・推定は行っていません。

## 導入

`index.html`、`labels_ja.json`、`reviews/v49_verified_translations.csv`、`tests/test_calendar_v49.py`、`.github/workflows/update.yml` をGitHubへ反映してください。

GitHub Actionsで `Test verified calendar translations V49 (offline)` の7項目を検証します。

参考： https://wikiwiki.jp/w-w/Ver3.7 、 https://wikiwiki.jp/w-w/素材獲得 、 https://wikiwiki.jp/w-w/響き渡る音弦
