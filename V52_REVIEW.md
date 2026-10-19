# V52｜未翻訳イベント名の追加確認

- 新たに3件を表示用 `labels_ja.json` に追加（原神1件、ゼンゼロ2件）。
- 既存の `events.json`、開催日時、配色、レイアウトは変更しない。
- `tests/test_calendar_v51.py` は前回の修正版を統合済み。
- `All-New Program` は公式サイトの記事ではなく、Wikiのゲーム内多言語表に明示された日本語名を使用。出典区分は `localization_index`。
- 原神の「勝者は誰だ！？」と英語告知の対応は多言語告知と日本語Wikiのイベント内容で確認。
- スタレ `Apocalyptic Shadow: Celestial Lupine` など残り7件は正式な日本語表記の根拠不足のため英語のまま。
- 自動取得によりイベント件数が変動しても失敗しないテスト。
