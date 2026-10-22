# Endfield V87 — full news inventory (read-only)

V86 verified that the official public API returns 131 total articles and 10 items per page when `tabs` is omitted. V87 paginates the unfiltered Japanese news list, saves article IDs/titles/categories/timestamps/briefs, and marks keyword matches for manual review. It does **not** import any article or modify `events.json` or the calendar.

## Upload these files
- `games/endfield/diagnose_v87.py`
- `tests/test_endfield_v87.py`

## Add before the existing `Commit changes` step in `.github/workflows/update.yml`
Keep all existing workflow steps; add only these:

```yaml
      - name: Test Endfield V87 (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v87.py' -v

      - name: Inventory Endfield official news V87 (read-only)
        run: python games/endfield/diagnose_v87.py

      - name: Upload Endfield V87 news inventory
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: endfield-news-inventory-v87
          path: .reports/endfield-v87/
          if-no-files-found: warn
          retention-days: 14
```

## Run
1. Upload the two files above.
2. Add the YAML steps above before `Commit changes`.
3. Run **Actions → Update Game Events → Run workflow**.
4. Download `endfield-news-inventory-v87` from Artifacts and upload its ZIP to this chat.

The script makes public GET requests only. Keyword matches are not automatically registered events; all results require review. Existing calendar design and `events.json` remain unchanged.
