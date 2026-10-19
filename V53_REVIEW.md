# V53 — verified localization and browser translation regression

- Added one independently checked Japanese name: `Advanced Bounty: Area Patrol` → `先遣賞金-区域防衛` (Zenless Zone Zero).
- Evidence: https://zenless-zone-zero.fandom.com/wiki/Advanced_Bounty%3A_Area_Patrol (the source explicitly lists both English and Japanese official names in its localization table; community-maintained evidence).
- Six other candidates remain unverified and are unchanged.
- Adds offline tests, including running the exact `translatedEvent` JavaScript extracted from `index.html` with Node, checking original name preservation, no mutation, and fallback.
- `events.json`, event dates, importer logic, and calendar design remain unchanged.
- Run: `python -m unittest discover -s tests -p 'test_calendar_v53.py' -v`.
- Recheck the displayed browser page after committing; tests do not exercise GitHub Pages deployment.
