# V49 テスト修正

GitHub Actions はデータ自動更新後にV49のテストを実行します。修正前は承認済み英語名12件が `events.json[*].name` にすべて存在し、かつ件数97・未翻訳件数28であることを要求していました。これらは自動更新で変わり得るため、正しい更新でも失敗します。

- `name` と `original_name`、翻訳済みの日本語 `name` に対応。
- イベントが更新で消えた場合は `REVIEW_NOT_IN_CURRENT_EVENTS` と出力し、辞書内容が正しい限りテストは失敗させません。
- 97件・28件という変動値に依存しないテストに変更。
- `labels_ja.json`、`index.html`、`events.json`、自動取込スクリプトは変更しません。
- ローカルで、元データ・日本語への改名・イベント削除の3ケースを検証済み。

GitHubで `tests/test_calendar_v49.py` を置換後、Actionsを再実行してください。
