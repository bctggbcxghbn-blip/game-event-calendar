# Endfield V94 — official notice review (read-only)

The official 「丹青渡」 notice (https://endfield.gryphline.com/ja-jp/news/9560) states relative end conditions for seven entries; it does **not** establish seven calendar end dates. This patch **does not fetch live notices**, **does not modify `events.json`**, and **does not change UI or other games**. It produces a fresh comparison against your repository's `events.json`.

Upload `tools/endfield_v94_official_review.py` and `tests/test_endfield_v94.py` to the same paths in GitHub. Add the following steps to `.github/workflows/update.yml` (do not replace the whole workflow):

```yaml
      - name: Endfield V94 official-source review
        run: python tools/endfield_v94_official_review.py

      - name: Upload Endfield V94 review
        uses: actions/upload-artifact@v4
        with:
          name: endfield-v94-official-review
          path: artifacts/endfield-v94/
          overwrite: true
```

Then run `Update Game Events` and upload the artifact `endfield-v94-official-review` here. To determine actual dates, an official announcement with the next maintenance start or third special-scout schedule is still needed.
