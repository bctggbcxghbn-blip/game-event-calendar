# Endfield V91 Artifact 409 修正

調査結果: 提供された update.yml には V91 のアップロードステップが1件だけあります。409は同一workflow run内に同名artifactが既に存在する場合に起きます。GitHub ActionsのRe-runで前回作成済みのartifactと衝突した可能性があります。

## 導入
1. ZIPの `.github/workflows/update.yml` をリポジトリの同じパスに上書きアップロードします。元のworkflowは保持し、V91 uploadに `overwrite: true` を1行だけ追加しています。
2. Actions > Update Game Events > Run workflow で新規実行してください。
3. Artifactsの `endfield-v91-reconciliation` をダウンロードして送ってください。

`overwrite: true` は同名artifactが存在する場合に置換します。V91のレポートにだけ適用し、events.jsonやUIは変更しません。なお Re-run と新規実行は異なり、新規実行は新しいrun IDを使います。
