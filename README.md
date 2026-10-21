# Endfield V74 — safe audit patch

This patch uses the **V73 snapshot from 2026-10-20** to compare named candidate events against the repository's current `events.json`. It does not fetch new articles, alter event data, or change the calendar UI. `possibly_registered` is an approximate name match, not verification of correct dates. The snapshot must be refreshed for newer articles.

Upload all three files preserving paths:
- `games/endfield/audit_v74.py`
- `games/endfield/endfield-v73-candidates.json`
- `tests/test_endfield_v74.py`

Insert before `Commit changes` in `.github/workflows/update.yml`:

```yaml
      - name: Test Endfield V74 audit (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v74.py' -v

      - name: Audit Endfield V73 candidates V74 (read-only)
        run: python games/endfield/audit_v74.py

      - name: Upload Endfield V74 audit
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-audit-v74
          path: .reports/endfield-v74/
          if-no-files-found: warn
          retention-days: 14
```

Then run `Update Game Events` manually and download `endfield-audit-v74` artifact. Note: V73 discovery may run in the same workflow, but this V74 patch compares the supplied snapshot, not the newly discovered report. Future version can connect the live report safely.
