# 7ゲームイベントカレンダー：自動同期の土台

## アップロード
このZIPを展開し、**中のファイルと `.github` フォルダ**を `game-event-calendar` リポジトリのルートにアップロードしてください。既存の `index.html` は置き換えます。GitHub Pages は `main` / `(root)` のままでOKです。

## できること
- サイトを開くと `events.json` の最新データを読み込みます。
- GitHub Actions が毎日 `update_events.py` を実行します。
- `sources.json` に指定した **HTTPSの公開JSONフィード**からイベントを取得し、`events.json` に統合します。
- イベントの手動追加・完了チェックは各ブラウザに保存されます（端末間同期はしません）。

## 重要な制限
**初期状態の `sources.json` は空です。** このままでは新イベントは自動発見・追加されません。7ゲームの正確な情報を公開JSONで提供する信頼できるデータ元を別途設定する必要があります。公式ニュースページを勝手に解析して日付を推測する仕組みは入れていません。

フィード形式はJSON配列です。例：
```json
[{"id":"genshin-example-2026","game":"genshin","name":"サンプルイベント","start":"2026-10-20","end":"2026-10-30","kind":"イベント","url":"https://example.org/"}]
```
ゲームID: `genshin`, `wuwa`, `hsr`, `zzz`, `nte`, `arknights`, `endfield`。

### 手動でデータを公開する場合
`events.json` に上記形式で追記すると、サイトを開いた際に反映されます。

### Actionsが書き込めない場合
Settings → Actions → General → Workflow permissions で **Read and write permissions** を有効にしてください。公開リポジトリのActions実行は利用枠や制限が適用される場合があります。
