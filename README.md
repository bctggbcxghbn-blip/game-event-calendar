# 鳴潮 V46 — HTTP 429 安全継続パッチ

## GitHubへの配置
- `games/wuwa/wuwa_wiki_runner_v46.py`
- `tests/test_wuwa_v46.py`

## `.github/workflows/update.yml` の変更（2か所のみ）

既存の `Import Wuwa Wiki auto V44` ステップを次のように変更します（ステップ名と `id` は維持）：

```yaml
      - name: Import Wuwa Wiki auto V44
        id: wuwa_wiki
        run: python games/wuwa/wuwa_wiki_runner_v46.py
```

このステップより**前**にテストを追加します：

```yaml
      - name: Test Wuwa V46 safe rate-limit handling (offline)
        run: python -m unittest discover -s tests -p 'test_wuwa_v46.py' -v
```

既存の監視レポートアップロードとEndfield以降のステップは変更しません。

## 挙動
- V44が成功：通常通り継続。
- V44がHTTP 429で停止し、ログに `NO_WRITES` があり、レポートと終了コードが一致：警告を出して他ゲームの更新を継続。
- それ以外の失敗：従来通りジョブを失敗にします。
- HTTP 429の回避や再試行追加はしません。既存キャッシュ・安全停止はそのままです。

注意：`NO_WRITES` はV43が出力した宣言に基づきます。ファイル内容の差分検証ではありません。
