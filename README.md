# Endfield V86 — read-only news tab discovery

V85 confirmed the official public news API responds, but `list` remained empty. V86 probes the API with an empty tab list, tab IDs 0–15, and a few combinations, then records response counts and limited field samples. It does not write to `events.json` or modify calendar data.

## Files to upload to the repository
- `games/endfield/diagnose_v86.py`
- `tests/test_endfield_v86.py`

## Add these steps to `.github/workflows/update.yml`
Insert before the existing `Commit changes` step. Keep all existing workflow steps.

```yaml
      - name: Test Endfield V86 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v86.py' -v

      - name: Diagnose Endfield news tab IDs V86 (read-only)
        run: python games/endfield/diagnose_v86.py

      - name: Upload Endfield V86 tab diagnostics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-tab-diagnostics-v86
          path: .reports/endfield-v86/
          if-no-files-found: warn
          retention-days: 14
```

## Run
1. Upload the two files above.
2. Add the workflow steps above before `Commit changes`.
3. Run **Actions → Update Game Events → Run workflow**.
4. Download artifact `endfield-tab-diagnostics-v86` and upload its ZIP to this chat.

The script makes public GET requests only. It does not modify `events.json`, add events, or change the calendar UI.
