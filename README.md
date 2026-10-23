# V90 — Endfield repository schema audit (read-only)

V90 is a diagnostic patch only. It does **not** change `events.json`, register events, alter the calendar UI, or replace the existing update workflow.

## Add these files

Copy into the repository, preserving paths:

- `tools/endfield_v90_repo_audit.py`
- `tests/test_endfield_v90_audit.py`

## Add steps to the existing `.github/workflows/update.yml`

Insert these steps after the repository checkout and Python setup, before the existing commit/push step. Keep all existing workflow steps:

```yaml
      - name: Test Endfield V90 audit (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v90_audit.py' -v

      - name: Run Endfield V90 repository audit (read-only)
        run: python tools/endfield_v90_repo_audit.py

      - name: Upload Endfield V90 audit report
        uses: actions/upload-artifact@v4
        with:
          name: endfield-v90-repo-audit
          path: |
            artifacts/endfield-v90-repo-audit.json
            artifacts/endfield-v90-repo-audit.md
          if-no-files-found: error
```

If the workflow has a different filename, add the steps to the workflow that runs the current event updater. Do not replace the workflow with a sample.

## Run and retrieve

1. Commit the files and workflow additions.
2. Open **Actions → Update Game Events → Run workflow**.
3. Download the `endfield-v90-repo-audit` artifact and upload it in the chat.

The report identifies the actual `events.json` schema, current Endfield entries, possible duplicate-key candidates, related importer scripts, and workflow files. V90 intentionally does not guess a schema or write events; the next patch can use the report to make a narrow, duplicate-safe integration.
