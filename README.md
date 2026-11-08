# 鳴潮 V47：V23 Wiki challenge HTTP 429 安全スキップ

## 適用
1. `games/wuwa/wuwa_auto_runner_v23.py` をGitHubの同じパスに上書き。
2. `tests/test_wuwa_v47.py` を同じパスに追加。
3. `.github/workflows/update.yml` の **Import Wuwa automatically V23** ステップはそのまま使う（変更不要）。
4. 任意で既存のワークフローの同ステップ直前にテストを追加：

```yaml
      - name: Test Wuwa V47 HTTP 429 handling
        run: python -m unittest discover -s tests -p 'test_wuwa_v47.py' -v
```

5. Actions → Update Game Events → Run workflow。

## 動作
- V22のチャレンジWiki抽出で明示的なHTTP 429、かつ `events.json` が当該ステップで未変更の場合のみ警告して継続。
- それ以外の失敗は従来どおり停止・ロールバック。
- 429時はWikiの古いキャッシュや推測日付を使用しない。
- 既存のV23の他の3つの取り込みと検証は維持。
- UI、`events.json`、ワークフロー本体はパッチに含めない。

注意：別ステップの429や他の失敗まではこの修正では解決しません。
