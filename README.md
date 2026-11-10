# Endfield V92 — 終了日未定の開始日マーカー

- `index.html` をルートで上書き。既存のレイアウト・配色は変更しません。
- `games/endfield/import_v92.py` を同じパスに追加。
- `.github/workflows/update.yml` の **Commit changes より前**（他のイベント取り込みの後）に以下を追加：

```yaml
      - name: Import Endfield V92 unknown-end start markers
        run: python games/endfield/import_v92.py
```

- Actions → Update Game Events → Run workflow。
- 終了日未定のイベントは開始日 **1日分のマーカー** として表示。開催中と誤認させる長いバーにはしません。
- 詳細に「終了：未定（開始日のみ表示）」と公式の終了条件を表示。
- 再実行しても同じIDを追加しません。既存11件や他ゲームのデータは変更しません。
- 終了日が後日判明したら、別の検証済み更新で補完してください。
- 注意：GitHub Actionsの他ステップが先に失敗した場合はこの取り込みは実行されません。
