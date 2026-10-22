# Endfield V85 — tabs 配列パラメータ診断

V84でAPIが `tabs must be an array` を返したため、読み取り専用GETで配列のクエリ表現を比較します。イベントデータ、`events.json`、カレンダーUIは変更しません。診断でHTTP 200になっても、記事一覧の形式を確認するまでは自動登録しません。

## 追加するファイル
- `games/endfield/diagnose_v85.py`
- `tests/test_endfield_v85.py`

## GitHub Actions
`update.yml` の既存のテスト・更新処理を削除せず、下記を **Commit changes** ステップより前に追加してください。

```yaml
      - name: Test Endfield V85 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v85.py' -v

      - name: Diagnose Endfield API tabs array V85 (read-only)
        run: python games/endfield/diagnose_v85.py

      - name: Upload Endfield V85 API diagnostics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-api-probe-v85
          path: .reports/endfield-v85/
          if-no-files-found: warn
          retention-days: 14
```

## 実行手順
1. ZIPを解凍し、2つのファイルを同じパスでリポジトリに追加します。
2. 上記YAMLを `update.yml` に追加してコミットします。
3. **Actions → Update Game Events → Run workflow** を実行します。
4. Artifacts の `endfield-api-probe-v85` をダウンロードし、このチャットにアップロードしてください。

## 読み取り専用の注意
- APIに対して公開GETリクエストのみ実行します。
- API応答本文の一部を診断レポートに記録します。
- 記事の自動登録、既存イベント変更、カレンダーUI変更は行いません。
