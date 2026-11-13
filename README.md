# Wuwa V51 — update.yml 重複処理修正

最新版リポジトリZIP（2026-11-13 07:43:40）を基に作成。

## 変更内容
- `Import Wuwa Wiki auto V44`（V46を引数なしで実行する旧ステップ）を削除。
- `Import Wuwa Wiki auto V46`（`--apply`）は残す。
- Endfield V94、キャッシュ復元、その他のゲーム処理は変更なし。

## 導入
GitHubリポジトリの `.github/workflows/update.yml` をこのZIP内の同名ファイルで置き換える。
その後 Actions → Update Game Events → Run workflow。

注意: このZIPはワークフローのみ。現在のGitHubにアップロード後の変更がある場合は上書き前に確認。
