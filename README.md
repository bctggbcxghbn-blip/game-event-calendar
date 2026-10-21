# エンドフィールド V79 — JavaScript内のニュース取得先を診断

V78でニュース一覧HTMLから記事URLを発見できなかったため、V79では公式ページが読み込む**同一ドメインのJavaScriptファイル**を調べ、ニュースAPIらしい文字列を抽出します。候補は未検証のため**APIにはアクセスしません**。`events.json` と既存の更新処理は変更しません。

## アップロードするファイル
- `games/endfield/diagnose_v79.py`
- `tests/test_endfield_v79.py`

## `.github/workflows/update.yml` の `Commit changes` より前に追加

```yaml
      - name: Test Endfield V79 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v79.py' -v

      - name: Diagnose Endfield JS news endpoints V79 (read-only)
        run: python games/endfield/diagnose_v79.py

      - name: Upload Endfield V79 diagnostics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-js-diagnostics-v79
          path: .reports/endfield-v79/
          if-no-files-found: warn
          retention-days: 14
```

## 次の手順
GitHub Actionsで `Update Game Events` を手動実行し、Artifactsの `endfield-js-diagnostics-v79` をこのチャットにアップロードしてください。レポートに含まれる `endpoint_candidates` を確認して、V80で実際に使える公式取得先かを検証します。

**注意:** JavaScriptにAPIのURLが含まれていない構成では候補が0件になる場合があります。これはエラーとは限りません。
