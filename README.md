# NTE V70 — duplicate audit (read-only)

Based on the user-supplied `events(5).json` (108 events, 15 NTE events). All four V69 candidates already exist. No event data or calendar UI is changed.

Copy `games/nte/nte_check_v70.py` and `tests/test_nte_v70.py` to matching paths in your GitHub repository. Do not delete existing files.

Run from repository root:

```bash
python -m unittest discover -s tests -p 'test_nte_v70.py' -v
python games/nte/nte_check_v70.py --events events.json
```

Audit output: `reports/nte-v70-audit.json` (generated locally). This patch does NOT edit `update.yml` or automatically schedule the audit. It is a safe read-only diagnostic, not a new-event discovery engine.
