# Endfield V77 — 公式新着記事の検出拡張（読み取り専用）

V76の実行結果では公式記事を1件しか確認できませんでした。V77は公式ニュース一覧・sitemap.xml・robots.txtに現れる記事URLを収集し、未確定7件と照合します。公式サイトが動的に記事を読み込む場合は、依然として全件を検出できない可能性があります。

## GitHubに追加するファイル
- `games/endfield/monitor_v77.py`
- `tests/test_endfield_v77.py`

**V76が必要です。** `games/endfield/monitor_v76.py` と V75の `pending_v75.json` はそのまま残してください。

## `.github/workflows/update.yml` の `Commit changes` より前に追加

```yaml
      - name: Test Endfield V77 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v77.py' -v

      - name: Monitor Endfield official news V77 (read-only)
        run: python games/endfield/monitor_v77.py

      - name: Upload Endfield V77 review
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-news-review-v77
          path: .reports/endfield-v77/
          if-no-files-found: warn
          retention-days: 14
```

GitHub Actionsでワークフローを実行後、Artifact `endfield-news-review-v77` をダウンロードしてください。

**安全性:** `events.json` や承認ファイルは変更しません。記事中の年月日は終了日と断定しません。`articles_discovered` が1のままなら公式ニュース一覧の動的読み込み等を調査する必要があります。
