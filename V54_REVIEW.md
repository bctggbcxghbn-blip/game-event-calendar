# V54: Display duplicate guard

- `events.json` and `labels_ja.json` are not modified.
- Only identical game, translated name, start, end, and event category are collapsed at display time.
- Separate periods, games, or gacha/event categories remain distinct.
- The workflow runs offline tests and a read-only duplicate audit after importers.
- Existing source importers are not changed. A later version can add importer-level deduplication after source-level review.
- V54 does not introduce unverified Japanese translations.
