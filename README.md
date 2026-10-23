# Endfield V88 — Official article detail diagnostic (read-only)

V87 successfully listed 131 official bulletin items. V88 fetches the official article detail endpoint for up to 35 high-relevance articles, prioritizing known article IDs `9560`, `2652`, `4489`, `7013`, `5207`, and `0744`. It saves detail responses and errors to `.reports/endfield-details-v88/report.json`.

**Safety:** this patch only makes public HTTP GET requests and writes a diagnostic report. It does not edit `events.json`, event data, the calendar UI, or any existing update script.

## Files
- `games/endfield/diagnose_v88.py`
- `tests/test_endfield_v88.py`

## Add these workflow steps before `Commit changes`
```yaml
      - name: Test Endfield V88 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v88.py' -v

      - name: Diagnose Endfield official article details V88 (read-only)
        run: python games/endfield/diagnose_v88.py

      - name: Upload Endfield V88 article detail report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-article-details-v88
          path: .reports/endfield-details-v88/
          if-no-files-found: warn
          retention-days: 14
```

## Run and return results
1. Upload the two files to the matching paths in the repository.
2. Add the three workflow steps above to `.github/workflows/update.yml` before the existing commit step. Keep all existing steps.
3. Run **Actions → Update Game Events → Run workflow**.
4. Download the `endfield-article-details-v88` artifact and upload its ZIP to the chat.
