# NTE V64 — V63 調査統合

既存リポジトリにV63の分類スクリプトとV62入力データ、生成したレビュー結果を統合。

- `nte_review_v63.py`: V62の56件を分類する読み取り専用スクリプト
- `nte_review_v62_input.json`: V62の入力レポート
- `nte-v63-output/`: 56件の分類（JSON/CSV/Markdown）

## 再実行
```bash
python games/nte/nte_review_v63.py --input games/nte/nte_review_v62_input.json --output games/nte/nte-v63-output
```

**注意**: V64は分類の統合であり公式ソースの新規検証ではありません。衣装割引とプカプラン・ハンター補給は未確定。イベントの自動登録は0件。既存UI、events.json、GitHub Actionsは未変更。
