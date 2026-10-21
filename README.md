# エンドフィールド V81 — ニュースAPI候補の安全な検証

V80で検出された `/api/bulletin` が実際に利用できるか調べる**診断専用パッチ**です。公式CDNのJavaScript内でAPI文字列の前後を抽出し、公式ドメインに対してGETを2回だけ試します。HTTPステータス、Content-Type、JSONのキーなどをレポートに残します。認証情報の取得やPOSTはしません。

**既存の events.json、デザイン、イベント更新処理は変更しません。** APIの存在や仕様はまだ確定していません。JavaScriptのファイル名が変わると取得できない場合があります。

## アップロードするファイル
- `games/endfield/diagnose_v81.py`
- `tests/test_endfield_v81.py`

## `.github/workflows/update.yml` の `Commit changes` より前に追加

```yaml
      - name: Test Endfield V81 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v81.py' -v

      - name: Diagnose Endfield bulletin API V81 (read-only)
        run: python games/endfield/diagnose_v81.py

      - name: Upload Endfield V81 API diagnostics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-api-diagnostics-v81
          path: .reports/endfield-v81/
          if-no-files-found: warn
          retention-days: 14
```

Actions → Update Game Events → Run workflow の後、Artifacts の `endfield-api-diagnostics-v81` をここにアップロードしてください。
