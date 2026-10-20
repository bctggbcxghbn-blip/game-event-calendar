# NTE V63 調査パッチ

V62の `report.json` だけを入力とする**読み取り専用**の追加解析です。既存の `events.json`、GitHub Actions、カレンダーのHTML/CSS/JSは変更しません。

## 実行

1. `nte-candidate-review-v62.zip` から `report.json` を取り出す。
2. リポジトリ直下で以下を実行する。

```bash
python scripts/nte_review_v63.py --input report.json --output nte-v63-output
```

3. `nte-v63-output/nte-review-v63.md`（人間向け）、`.csv`（56件の一覧）、`.json`（構造化結果）を確認。

## 注意
- V62候補70件のうち未一致56件のみ詳細分類。13件の一致情報は維持。
- V62候補の文章と既存イベントとの関連付けは**調査用仮説**。元記事での前後関係を要確認。
- 衣装割引の日時、JSTとサーバー時間の差は自動確定しない。
- 新規登録・自動修正は0件。カレンダーデザインに影響しない。
