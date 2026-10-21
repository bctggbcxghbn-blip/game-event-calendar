# エンドフィールド V83 — 設定モジュール56006の調査

公式ニュースページが読み込むJavaScriptを最大45件解析し、Webpackモジュール `56006` の**定義部分**を探して、その周辺コードを診断レポートに保存します。V82で確認できた `cms.host` と `cms.appCode` の値を特定するための調査です。取得した文字列は未検証で、API接続やイベント変更は行いません。

## 追加ファイル
- `games/endfield/diagnose_v83.py`
- `tests/test_endfield_v83.py`

## `.github/workflows/update.yml` の `Commit changes` より前に追加

```yaml
      - name: Test Endfield V83 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v83.py' -v

      - name: Diagnose Endfield config module V83 (read-only)
        run: python games/endfield/diagnose_v83.py

      - name: Upload Endfield V83 config diagnostics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-config-module-v83
          path: .reports/endfield-v83/
          if-no-files-found: warn
          retention-days: 14
```

Actions実行後、Artifact `endfield-config-module-v83` をアップロードしてください。
