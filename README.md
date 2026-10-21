# エンドフィールド V80 — 公式CDNのニュース用JavaScript診断

V79のレポートで、公式ニュースページのJavaScriptが `web-static.hg-cdn.com` に置かれていることが分かりました。V80はこの公式ページから参照されるCDN上のJavaScriptを読み取り、ニュースAPIらしいURLの候補を抽出します。V79で見つかったニュース用JSも取得対象に含めます。

**読み取り専用です。** `events.json`、カレンダーデザイン、既存の更新処理は変更しません。抽出した文字列は未検証で、APIへのリクエストは行いません。

## GitHubに追加するファイル
- `games/endfield/diagnose_v80.py`
- `tests/test_endfield_v80.py`

## `.github/workflows/update.yml` の `Commit changes` より前に追加

```yaml
      - name: Test Endfield V80 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v80.py' -v

      - name: Diagnose Endfield CDN JS V80 (read-only)
        run: python games/endfield/diagnose_v80.py

      - name: Upload Endfield V80 diagnostics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-cdn-js-v80
          path: .reports/endfield-v80/
          if-no-files-found: warn
          retention-days: 14
```

Actions → Update Game Events → Run workflow を実行して、Artifacts の `endfield-cdn-js-v80` をアップロードしてください。V81で候補を検証します。

**注意**: CDNファイル名はサイト更新により変わる可能性があります。取得失敗時は `report.json` の `error` を確認してください。
