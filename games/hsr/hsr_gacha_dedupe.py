#!/usr/bin/env python3
"""Remove two specifically identified, overlapping Wiki HSR warp rows.

Run AFTER wiki_hsr_gacha.py AND hsr_official_gacha_apply.py.
Preview by default; --apply writes only after strict validation.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / 'events.json'
OFFICIAL = 'https://www.hoyolab.com/article/46851682'
PAIRS = {
    'パール': ('wiki-hsr-gacha-20d200007ca146c89d09', 'wiki-hsr-gacha-c5eea1d917d6d611e256'),
    '明日に捧げる色': ('wiki-hsr-gacha-36d139ba0992c9be15b8', 'wiki-hsr-gacha-180b4ecf05d9600cc1e9'),
}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    rows = json.loads(PATH.read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('events.json must be a list')
    by_id = {}
    for row in rows:
        if isinstance(row, dict) and row.get('id'):
            if row['id'] in by_id:
                raise RuntimeError('Duplicate ID: ' + row['id'])
            by_id[row['id']] = row
    remove = set()
    for name, (official_id, stale_id) in PAIRS.items():
        first, second = by_id.get(official_id), by_id.get(stale_id)
        if first is None or second is None:
            raise RuntimeError(f'Missing expected pair for {name}; refusing to modify')
        expected_first = {'game': 'hsr', 'name': name, 'start': '2026-09-28',
                          'end': '2026-11-10', 'end_time': '16:00',
                          'start_label': 'アップデート後', 'official_url': OFFICIAL}
        expected_second = {'game': 'hsr', 'name': name, 'start': '2026-10-21',
                           'end': '2026-11-11'}
        for label, row, expected in [('official', first, expected_first), ('stale', second, expected_second)]:
            bad = {k: (row.get(k), v) for k, v in expected.items() if row.get(k) != v}
            if bad:
                raise RuntimeError(f'{name} {label} mismatch {bad}; refusing to modify')
        if second.get('official_url'):
            raise RuntimeError(f'{name}: second row has an official source; refusing to modify')
        remove.add(stale_id)
        print(f'OVERLAP: {name} | keep {official_id} | remove {stale_id}')
    print(f'Mode: {"APPLY" if args.apply else "PREVIEW"}; candidates={len(remove)}')
    if not args.apply:
        print('events.json unchanged')
        return
    updated = [r for r in rows if not (isinstance(r, dict) and r.get('id') in remove)]
    fd, tmp = tempfile.mkstemp(prefix='.events-', suffix='.json', dir=PATH.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(updated, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(tmp, PATH)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(f'Removed {len(remove)} duplicate Wiki rows; retained {len(updated)} events')

if __name__ == '__main__':
    main()
