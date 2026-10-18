# Game Event Calendar — V41 code review and changes

## Source
Reviewed the user-provided `game-event-calendar-main(1).zip` snapshot. The root `events.json` contains 97 records. This is a modified copy; the original ZIP was not overwritten.

## Main findings
1. `.github/workflows/update.yml` runs many legacy Wuwa probes (V1–V34), plus many ZZZ/HSR diagnostics on every scheduled run. This increases request volume and makes a single transient error fail the workflow before later importers run.
2. V40 fetched four index pages and up to four version pages every run without cache or 429 retry; the observed 429 is consistent with excessive requests, although server-side cause cannot be proven from this repository alone.
3. V40's period-aware matching is better for reruns, but the fixed `PROTECTED_OFFICIAL_IDS` alias for 曇斬 is version-specific and should eventually be replaced by general source/article identity matching.
4. V35 parser relies on table column positions and anchor labels; site layout changes or one-character names (心) still need manual review.
5. `events.json` mixes date-only strings and timezone-bearing timestamps. V41 preserves this and never invents JST hours.
6. ZZZ `zzz_challenge_prediction_import.py --apply` was enabled in the old daily workflow. It is removed from the cleaned schedule because predictions should not silently become authoritative dates. The file remains in the repository for manual review.
7. The original workflow had no concurrency guard; the cleaned workflow serializes updates.

## V41 changes
- Two Wiki index pages instead of four; two newest version pages by default instead of four.
- On-disk HTML cache (24-hour TTL) restored/saved with GitHub Actions cache; only validated fresh cached pages are used.
- Bounded HTTP 429 and transient 5xx retries with exponential pauses. If a page cannot be fetched, stop without writing; no stale cache fallback on apply.
- Fetch and parse all pages before launching V40 importer. Retains V40 dedupe, backups and official-record precedence.
- Replaces legacy Wuwa probes and scheduled preview-only diagnostics with V23, V29, V41. Removes legacy preview-only steps for other games while retaining selected operational importers.
- Leaves all old source scripts in place for manual debugging and keeps all 97 records unchanged.

## Important limits
- V41's index-link discovery can still miss unlinked versions.
- V41 depends on `wuwa_wiki_merge_preview_v35.py` and `wuwa_wiki_gacha_import_v40.py`.
- Cache is best-effort: first run after cache expiry may still receive 429 and stop safely. Retry delays are 3 and 6 seconds by default.
- The cleaned workflow has NOT been tested against live Wiki, official APIs, or all other games. Run `workflow_dispatch` and inspect logs before relying on the scheduled job.
- HSR and ZZZ importers may have ordering/dependency subtleties; no attempt was made to rewrite their algorithms. Check their logs after replacing the workflow.

## Files
- `games/wuwa/wuwa_wiki_auto_runner_v41.py`: new runner.
- `.github/workflows/update.yml`: simplified schedule and cache.
- `V41_REVIEW.md`: this report.
