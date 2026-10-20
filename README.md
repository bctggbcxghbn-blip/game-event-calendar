# エンドフィールド V73 — 公式記事の自動検出（読み取り専用）

既存のカレンダーデザイン、`events.json`、NTEなどの更新処理は変更しません。

## 追加するファイル
- `games/endfield/discover_v73.py`
- `tests/test_endfield_v73.py`

## `.github/workflows/update.yml` に追記
既存の `Commit changes` ステップより前に以下を挿入してください（既存の `update.yml` 全体は上書きしない）。

```yaml
      - name: Test Endfield discovery V73 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v73.py' -v

      - name: Discover Endfield official news V73 (read-only)
        run: python games/endfield/discover_v73.py

      - name: Upload Endfield V73 candidate report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-candidates-v73
          path: reports/endfield-v73-candidates.json
          if-no-files-found: warn
```

## 実行結果
Actions の `endfield-candidates-v73` Artifact からJSONレポートを取得できます。候補文はイベント確定データではありません。記事のHTML構造やJavaScriptレンダリングの変更で候補を拾えない場合があります。開催日時と既存イベントとの照合は次の段階で行います。**自動登録は0件です。**
