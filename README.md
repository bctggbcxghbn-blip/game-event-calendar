# HSR V93 — 重複削除処理の再実行安全化

## 手順
1. `games/hsr/hsr_gacha_dedupe.py` をGitHubの同じパスに上書き。
2. `tests/test_hsr_v93.py` を追加（任意のローカルテスト用）。
3. Actions → Update Game Events → Run workflow を実行。

`update.yml`、`events.json`、UIは変更不要。

## 挙動
- 公式IDがあり、古いIDがない: 公式行の日時と出典を検証してスキップ。
- 両方ない: 過去対象がないためスキップ。
- 古いIDだけある: エラーで停止。
- 両方ある: 元の厳格な照合を維持して古いIDだけ削除。
- 公式行が想定外の値: エラーで停止。

テスト: `python -m unittest discover -s tests -p 'test_hsr_v93.py' -v`
