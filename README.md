# エンドフィールド V82 — CMS設定・API接続先の診断

V81で `/api/bulletin` の呼び出し構造は分かったものの、公式サイト直下では404でした。V82は公式ニュースページが参照するJavaScript（最大12件）から `appCode`、`baseURL`、`cms`、`tabs` 等の設定候補を抽出し、取得状況をレポートに記録します。

**診断専用**です。APIにリクエストを送らず、`events.json`、既存の更新処理、デザインは変更しません。候補は未検証で、設定値の確定には次の分析が必要です。

## 追加ファイル
- `games/endfield/diagnose_v82.py`
- `tests/test_endfield_v82.py`

## `.github/workflows/update.yml` の `Commit changes` より前に追加

```yaml
      - name: Test Endfield V82 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v82.py' -v

      - name: Diagnose Endfield CMS config V82 (read-only)
        run: python games/endfield/diagnose_v82.py

      - name: Upload Endfield V82 CMS diagnostics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-cms-diagnostics-v82
          path: .reports/endfield-v82/
          if-no-files-found: warn
          retention-days: 14
```

Actionsで実行したらArtifact `endfield-cms-diagnostics-v82` をダウンロードしてチャットにアップロードしてください。
