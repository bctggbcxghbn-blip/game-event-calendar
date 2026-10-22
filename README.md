# エンドフィールド V84 — 公式ニュースAPI接続テスト

V83で確認した `https://web-news.gryphline.com` と `arknights_endfield_official` を使い、公開ニュース一覧のGETリクエストを最大4パターンだけ試します。JSONの構造と記事タイトルの短いプレビューを診断レポートに記録します。APIの応答形式は未検証なので、イベント登録・終了日変更・`events.json` の編集は一切行いません。

## 追加ファイル
- `games/endfield/diagnose_v84.py`
- `tests/test_endfield_v84.py`

## GitHub Actionsへの追加
`.github/workflows/update.yml` の既存 `Commit changes` ステップより前に、次の3ステップを追加してください。

```yaml
      - name: Test Endfield V84 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v84.py' -v

      - name: Diagnose Endfield bulletin API V84 (read-only)
        run: python games/endfield/diagnose_v84.py

      - name: Upload Endfield V84 API probe report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-api-probe-v84
          path: .reports/endfield-v84/
          if-no-files-found: warn
          retention-days: 14
```

実行後、Artifactsの `endfield-api-probe-v84` をダウンロードして、このチャットにアップロードしてください。HTTP 200だけでは記事取得成功と判断せず、JSON構造と記事タイトルを確認してから次段階に進みます。
