# エンドフィールド V72 パッチ（丹青渡）

公式: https://endfield.gryphline.com/ja-jp/news/9560

既存カレンダーのデザインは変更しません。**events.json は同梱していません。**

## 導入
ZIP内の `games/endfield/` と `tests/test_endfield_v72.py` をリポジトリに追加。

```bash
python -m unittest discover -s tests -p 'test_endfield_v72.py' -v
python games/endfield/import_v72.py          # プレビュー
python games/endfield/import_v72.py --apply  # events.json に追記
```

GitHub Actionsの `update.yml` で自動実行する場合、`Commit changes` の直前に以下のステップを追加してください（既存のworkflow全体は上書きしないでください）。

```yaml
      - name: Import Endfield Danqingdu V72
        run: python games/endfield/import_v72.py --apply
```

## 注意
- 公式記事で終了日が明示されている11件のみ収録。無期限・次回メンテまでのイベントは、終了日未確定のため保留。
- 「丹青渡開始後」は10月15日付けで記録し、正確な開始時刻は未確定として扱います。
- 日時は原則サーバー時間。JSTへの自動変換はしません。
- Asiaサーバーの「理性補給」を採用しています。
- 今回は新規イベントを探し続ける自動発見ではなく、公式確認済み11件を重複なく取り込む処理です。
