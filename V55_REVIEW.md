# V55 鳴潮の取得データ重複整理

- `games/wuwa/wuwa_final_dedupe_v55.py` を全インポート後・コミット前に実行。
- 鳴潮に限定し、翻訳後の表示名・開始日・終了日・分類が一致し、**公式告知由来1件と未確認外部API由来1件の2件だけ**の場合、外部API由来を除外する。
- 同じ名前でも開催期間が違う復刻や、ガチャ分類の違うデータ、判定が曖昧なグループは削除しない。
- `--apply` で `events.json.v55.bak` を作ってから `events.json` を更新。バックアップはActionsでは一時ファイルであり、自動コミットされない。
- 現在の97件を対象にした試験では5件が除外候補（97→92）。更新用ZIPには元の97件の `events.json` を含めない。
- 既存のV54テストは重複がすでに解消されていても通るように修正。
- 画面側のV54重複防止はそのまま残す。

## ローカル確認

```
python -m unittest discover -s games/wuwa -p 'test_wuwa_final_dedupe_v55.py' -v
python -m unittest discover -s tests -p 'test_calendar_v54.py' -v
python games/wuwa/wuwa_final_dedupe_v55.py
```

GitHub Actionsでは V55 テスト → V55 --apply → V54 テスト・監査 → Commit の順で実行。
