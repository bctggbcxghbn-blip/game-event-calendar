# Endfield V89 patch — verified date candidates (review only)

This patch records seven Endfield events/scout banners grounded in the V88 report of official bulletin article CID `9560` (and CID `2652` for 「玉書・申請」).

## Included files

- `games/endfield/v89_verified_candidates.json`: seven review-only candidate records.
- `tests/test_endfield_v89.py`: offline validation tests.

## Important safety/data behavior

- This patch **does not edit `events.json`** and does not change the calendar UI.
- Every candidate remains `review_required`.
- Exact start dates/times and source wording are preserved where available.
- Relative end conditions are kept as text; end dates are intentionally `null` rather than guessed.
- The Dec 3, 2026 04:00 deadline in the article is the 「機密聖堂」 reward shop deadline, not the confirmed end of 「危機契約 青藍試験作戦」 itself.

## Install

1. Download and extract this ZIP.
2. Upload `games/endfield/v89_verified_candidates.json` to the same path in the GitHub repository.
3. Upload `tests/test_endfield_v89.py` to `tests/test_endfield_v89.py`.
4. If the existing workflow already runs `python -m unittest discover -s tests`, the test will be picked up automatically. Otherwise, add this step before the existing commit step without replacing any existing workflow steps:

```yaml
      - name: Test Endfield V89 verified candidates (offline)
        run: python -m unittest discover -s tests -p 'test_endfield_v89.py' -v
```

5. Run **Actions → Update Game Events → Run workflow** and check the test result.

This is a staging patch only. It does not import the candidates into the live calendar; the next patch can connect reviewed candidates to the existing importer after the repository's current data schema is confirmed.
