# ゲーム別スクリプト

- `hsr/`: 崩壊：スターレイル。既存の取得・照合スクリプトをまとめています。
- `genshin/`: 原神（現時点で専用スクリプトなし）
- `wuwa/`: 鳴潮（同上）
- `zzz/`: ゼンレスゾーンゼロ（同上）
- `nte/`, `arknights/`, `endfield/`: 今後の拡張用。

共通の `update_events.py` はルートに残し、`events.json`、`sources.json`、`labels_ja.json` もルートで共有します。

GitHub Actions の `update.yml` は新しいパスを使用します。
