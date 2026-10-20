# V67 NTE GitHub Actions パッチ

既存の `game-event-calendar-main(4).zip` の `update.yml` を元に、NTE ハンター褒章の重複防止登録処理を追加しました。UI/CSSは変更しません。

## 導入
ZIPの次の3ファイルを、GitHubリポジトリの**同じパス**にアップロードしてください。

- `.github/workflows/update.yml`（既存ファイルを置換）
- `games/nte/nte_v67_add_hunter.py`（追加）
- `tests/test_nte_v67.py`（追加）

`Actions` → `Update Game Events` → `Run workflow` で手動実行し、ログの `Import NTE Hunter Pass V67` と `Commit changes` を確認してください。

## 動作
毎日のワークフローにNTE V67を追加します。既存のNTE V59とV60～V62の処理は維持します。対象イベントが登録済みならスキップします。新規なら `events.json` に1件追加し、既存のコミット処理で保存します。

**注意**: V67は公式サイトから新しいイベントを自動発見する機能ではありません。検証済みのハンター褒章1件を冪等に追加するものです。公式告知の日時は再検証が必要なら確認してください。元ZIP以降に `update.yml` が更新されている場合は丸ごと上書きせず差分を統合してください。
