#!/usr/bin/env python3
"""WuWa V23: run the existing validated importers safely as one daily job.

This is orchestration, NOT dynamic discovery of new official article IDs.
Preview by default. --apply uses the importers' --apply switches.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / 'events.json'
STEPS = [
    ('Official maintenance + character events (fixed articles)', 'wuwa_safe_import_v14.py'),
    ('Official weapon banners (fixed article)', 'wuwa_gacha_import_v17.py'),
    ('Official server-date events (fixed article)', 'wuwa_server_date_import_v20.py'),
    ('Wiki challenge periods (current pages)', 'wuwa_challenge_import_v22.py'),
]

def read_events():
    obj = json.loads(EVENTS.read_text(encoding='utf-8-sig'))
    if not isinstance(obj, list) or any(not isinstance(e, dict) for e in obj):
        raise ValueError('events.json must be a list of objects')
    ids = [e.get('id') for e in obj if e.get('id') is not None]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate event IDs in events.json')
    return obj

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='append validated new records')
    args = parser.parse_args()
    print('WUWA V23 DAILY RUNNER /', 'APPLY' if args.apply else 'PREVIEW', flush=True)
    print('NOTE: official importers still use fixed article IDs; new versions need a later dynamic importer.', flush=True)
    if not EVENTS.is_file():
        raise SystemExit('ERROR: events.json not found at repo root: ' + str(EVENTS))
    try:
        original = read_events()
    except Exception as exc:
        raise SystemExit('ERROR: invalid events.json: ' + str(exc))
    here = Path(__file__).resolve().parent
    missing = [filename for _, filename in STEPS if not (here / filename).is_file()]
    missing += [filename for filename in ('wuwa_safe_import_v13.py', 'wuwa_server_date_preview_v19.py') if not (here / filename).is_file()]
    if missing:
        raise SystemExit('ERROR: missing required files in games/wuwa/: ' + ', '.join(missing))
    backup = None
    if args.apply:
        with tempfile.NamedTemporaryFile(prefix='wuwa-v23-backup-', suffix='.json', delete=False) as f:
            backup = Path(f.name)
        shutil.copy2(EVENTS, backup)
    try:
        for label, filename in STEPS:
            print('\nSTEP:', label, flush=True)
            command = [sys.executable, str(here / filename)] + (['--apply'] if args.apply else [])
            proc = subprocess.run(command, cwd=ROOT, check=False)
            if proc.returncode:
                raise RuntimeError(f'{filename} failed (exit={proc.returncode})')
            # Preview scripts must never modify the file.
            if not args.apply and read_events() != original:
                raise RuntimeError(f'{filename} modified events.json in preview mode')
        current = read_events()
        if len(current) < len(original) or current[:len(original)] != original:
            raise RuntimeError('existing events were removed or modified')
        added = current[len(original):]
        if len(added) > 30:
            raise RuntimeError(f'unsafe number of new records: {len(added)} (>30)')
        if any(str(e.get('game', '')).lower() != 'wuwa' for e in added):
            raise RuntimeError('unexpected non-WuWa event added')
        print(f'\nSUMMARY: before={len(original)} added={len(added)} total={len(current)}', flush=True)
        print('APPLY COMPLETE.' if args.apply else 'PREVIEW COMPLETE. events.json unchanged.', flush=True)
    except Exception as exc:
        if backup is not None:
            shutil.copy2(backup, EVENTS)
            print('ROLLBACK: events.json restored to pre-run state.', flush=True)
        raise SystemExit('ERROR: ' + str(exc))
    finally:
        if backup is not None:
            backup.unlink(missing_ok=True)

if __name__ == '__main__':
    main()
