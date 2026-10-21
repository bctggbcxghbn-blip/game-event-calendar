# エンドフィールド V78 — 新着記事取得の診断（読み取り専用）

V77のレポートで公式記事が1件しか見つからなかったため、ニュース一覧・サイトマップ・robots.txt のHTTP応答とリンク抽出を可視化します。**記事を新規登録したり、終了日を承認したりはしません。**

## GitHubに追加するファイル
- `games/endfield/diagnose_v78.py`
- `tests/test_endfield_v78.py`

**依存:** V76の `games/endfield/monitor_v76.py` とV77の `games/endfield/monitor_v77.py` は残してください。

## `.github/workflows/update.yml` の `Commit changes` より前に追加

```yaml
      - name: Test Endfield V78 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v78.py' -v

      - name: Diagnose Endfield news discovery V78 (read-only)
        run: python games/endfield/diagnose_v78.py

      - name: Upload Endfield V78 diagnostics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-discovery-diagnostics-v78
          path: .reports/endfield-v78/
          if-no-files-found: warn
          retention-days: 14
```

## 実行後
Actions → Update Game Events → Run workflow → Artifact `endfield-discovery-diagnostics-v78` をダウンロードして、このチャットにアップロードしてください。

`report.json` の `sources` に取得先ごとの `http_status`、`final_url`、`content_type`、`html_anchor_count`、`anchor_samples`、`new_article_count`、`error` が出力されます。HTML全文や個人情報は保存しません。記事の発見件数が1件なら警告を出します。カレンダーの `events.json` は変更しません。
