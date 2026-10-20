# NTE V71 — safe reviewed-only import

V71 integrates with the V68 daily discovery step, but **does not infer event dates from nearby text**. New articles continue to be reported as candidates. Only entries manually verified and added to `games/nte/approved/v71.json` with `reviewed: true`, exact `start`/`end`, and a NTE official URL can be imported. The manifest is deliberately empty, so this patch adds **zero** events until reviewed entries are supplied.

Upload these four files preserving paths:
- `.github/workflows/update.yml` (replace; based on V68/V67 workflow)
- `games/nte/nte_import_v71.py`
- `games/nte/approved/v71.json`
- `tests/test_nte_v71.py`

Run Actions → Update Game Events → Run workflow. The `nte-review-v71` artifact reports approved additions, duplicates and rejected records. Raw V68 candidates are **never** directly imported. V67 and V68 steps remain. Calendar HTML/CSS unchanged.

**Caution:** If `update.yml` has changed since V68, merge only the three V71 steps before `Commit changes` rather than replacing newer workflow modifications. Approvals should only be entered after verifying the official event period, not based on a date near a candidate sentence. V71 does not yet provide autonomous reliable date verification or a fully automatic new-event importer.
