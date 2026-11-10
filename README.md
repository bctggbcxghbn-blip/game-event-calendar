# 鳴潮 V48 — Endfield V92 終了日未定マーカーとの互換性修正

## 配置
1. `games/wuwa/wuwa_dynamic_gacha_import_v29.py` を同じパスに上書き。
2. `tests/test_wuwa_v48.py` を同じパスに追加。
3. `.github/workflows/update.yml` は変更不要。
4. Actions → Update Game Events → Run workflow を実行。

## 変更点
- `end: null` を認めるのは Endfield V92 の公式開始日確認済み・終了日未定マーカーに限る。
- 他ゲームの終了日欠損、重複ID、既存レコードの改変は引き続きエラー。
- ガチャ取得・登録のロジックやカレンダー表示は変更しない。

## テスト
`python -m unittest discover -s tests -p 'test_wuwa_v48.py' -v`

注意: ZIPのevents.jsonは151件で終了日欠損がなく、実行中に追加されるV92マーカーが今回の不整合原因と考えられます。実際のActionsで再確認してください。
