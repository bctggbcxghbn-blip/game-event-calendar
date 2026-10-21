# Endfield V76 — official notice end-date monitoring

Read-only monitor for the 7 V75 pending events. Scans the official Japanese news index (up to 20 linked articles plus the original notice), searches for event names and date mentions, and writes a review artifact. It does NOT decide which date is the end date, modify `events.json`, or change `approved_ends_v75.json`.

Upload these two files to your repository:
- `games/endfield/monitor_v76.py`
- `tests/test_endfield_v76.py`

The script reads the **existing** `games/endfield/pending_v75.json`, so V75 must already be installed.

Add the following steps to `.github/workflows/update.yml` before `Commit changes`:

```yaml
      - name: Test Endfield V76 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v76.py' -v

      - name: Monitor Endfield official end dates V76 (read-only)
        run: python games/endfield/monitor_v76.py

      - name: Upload Endfield V76 review
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-enddate-review-v76
          path: .reports/endfield-v76/
          if-no-files-found: warn
          retention-days: 14
```

Then run Actions > Update Game Events > Run workflow and upload the `endfield-enddate-review-v76` artifact here.

**Caution:** A date found near an event name is only a clue, not an approved end date. The report records `verified_end: null` for every event. Review the cited official notice manually before adding a verified date to the V75 approval file. Some news listing entries may be loaded dynamically and not appear in HTML links; the original official article is always included.
