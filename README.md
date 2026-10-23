# Endfield V91 ZIP patch

Purpose: read-only reconciliation of the 7 V89 candidates against the actual `events.json` schema and registered Endfield rows.

## Copy these files into the repository
- `tools/endfield_v91_reconcile.py`
- `tests/test_endfield_v91_reconcile.py`

Do not replace `events.json`, `update_events.py`, `import_v75.py`, or the existing workflow.

## Add steps to `.github/workflows/update.yml`
Place these steps near the existing V90 audit steps, before the import steps. Keep all existing workflow steps:
```yaml
      - name: Test Endfield V91 reconciliation (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v91_reconcile.py' -v

      - name: Reconcile Endfield V89 candidates V91 (read-only)
        run: python tools/endfield_v91_reconcile.py

      - name: Upload Endfield V91 reconciliation report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-v91-reconciliation
          path: .reports/endfield-v91/
          if-no-files-found: warn
          retention-days: 14
```
## Expected behavior
- Does not modify `events.json`.
- Detects exact ID and normalized exact-name matches.
- Lists similar names as manual-review hints only.
- Candidates without verified end dates remain `waiting_for_verified_end`.
- Upload the `endfield-v91-reconciliation` artifact here for the next step.
