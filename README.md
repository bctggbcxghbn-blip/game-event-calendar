# 鳴潮 V49 HTTP 429 修正

今回の最新版リポジトリには、鳴潮Wiki更新が2回ありました（29行付近と50行付近）。前者はキャッシュ復元前、後者は復元後です。V49は前者を削除し、後者だけを残します。

## 導入
1. ZIPの `.github/workflows/update.yml` をGitHubの同じ場所に上書き。既存の個別編集と競合する場合は差分を確認。
2. `games/wuwa/wuwa_wiki_runner_v46.py` を上書き。
3. `tests/test_wuwa_v49.py` を追加（任意）。
4. Actions > Update Game Events > Run workflow で新規実行。

## 動作
トップページの `STOP_INDEX_ERROR` とバージョンの `STOP_VERSION_ERROR` のどちらも、レポートに429が記録され `NO_WRITES` が確認できた場合のみ警告として続行します。その他のエラーは停止します。
`events.json`、画面デザイン、Endfieldの処理は変更しません。
