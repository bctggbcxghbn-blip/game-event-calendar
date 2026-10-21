# Endfield V75 — conditional-date safe importer

Latest events.json review: 127 total, 11 Endfield entries, 7 missing candidates.

This patch does NOT invent end dates. All 7 are held in pending_v75.json. The approved_ends_v75.json file starts empty, so the default import makes no changes.

Upload these three files to the repository at their included paths:
- games/endfield/import_v75.py
- games/endfield/pending_v75.json
- games/endfield/approved_ends_v75.json
- tests/test_endfield_v75.py

Add to `.github/workflows/update.yml` before `Commit changes`:

      - name: Test Endfield V75 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v75.py' -v

      - name: Import Endfield verified end dates V75
        run: python games/endfield/import_v75.py --apply

      - name: Upload Endfield V75 review
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-review-v75
          path: .reports/endfield-v75/
          if-no-files-found: warn
          retention-days: 14

When an end date is verified, edit `approved_ends_v75.json` with the event ID and YYYY-MM-DD end date, e.g. {"endfield-v75-minho":{"end":"YYYY-MM-DD"}} (replace placeholder with a verified date). Never approve based on an estimate.

The importer is idempotent by ID and exact name. The UI and all other games are unchanged. The 7 candidates' start dates and end conditions come from the V74 official-article audit; specific start times omitted where unverified.
