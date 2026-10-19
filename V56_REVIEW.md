# V56: Calendar update audit

- Run **after all import and V55 deduplication steps**, before committing.
- Read-only `tests/calendar_update_audit_v56.py --strict` checks malformed dates, reversed dates, missing required fields and duplicate IDs. Critical errors fail the workflow to prevent committing bad data.
- Matching game/name/period/kind with different IDs is **review-only** (no deletion, no failure).
- Change counts compare working `events.json` to `git show HEAD:events.json`; if unavailable, the report clearly says so.
- A report is uploaded as the `calendar-update-quality-v56` GitHub Actions artifact even on failure.
- This does not change events, translations, or frontend design. Changes to sources may still need manual verification.
