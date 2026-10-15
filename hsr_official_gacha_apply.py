#!/usr/bin/env python3
"""Conservative, reviewed mapping of HSR v4.6 Phase I warps.

Default is preview-only. Use --apply to modify events.json.
Run AFTER wiki_hsr_gacha.py because that importer rebuilds wiki-gacha rows.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVENTS = ROOT / 'events.json'
OFFICIAL = 'https://www.hoyolab.com/article/46851682'
START = '2026-09-28'
# Explicit identity mapping based on official article passages and Japanese Wiki names.
# End clock is Asia server UTC+8 converted to JST UTC+9.
MAPPING = {
    'パール': ('2026-11-10', '16:00', 'Pearl'),
    '明日に捧げる色': ('2026-11-10', '16:00', 'Colors for Tomorrow'),
    '緋英': ('2026-10-21', '12:59', 'Evanescia'),
    '再び花が咲く季節に': ('2026-10-21', '12:59', 'Until the Flowers Bloom Again'),
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Write verified changes')
    args = parser.parse_args()
    rows = json.loads(EVENTS.read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('events.json must contain an array')
    changed = 0
    matched = set()
    for e in rows:
        if not isinstance(e, dict) or e.get('game') != 'hsr' or e.get('start') != START:
            continue
        if not str(e.get('id', '')).startswith('wiki-hsr-gacha-'):
            continue
        name = e.get('name')
        if name not in MAPPING:
            continue
        if name in matched:
            raise RuntimeError(f'Duplicate banner row for {name}; refusing to write')
        matched.add(name)
        end, end_time, english = MAPPING[name]
        if e.get('end') not in ('2026-10-21', end):
            raise RuntimeError(f'Unexpected end date for {name}: {e.get("end")}')
        if e.get('end_time') not in (None, '12:59', end_time):
            raise RuntimeError(f'Unexpected end time for {name}: {e.get("end_time")}')
        if e.get('official_url') not in (None, OFFICIAL):
            raise RuntimeError(f'Conflicting official URL for {name}')
        updates = {'end': end, 'end_time': end_time,
                   'start_label': 'アップデート後', 'official_url': OFFICIAL,
                   'source_status': 'HoYoLAB公式認証投稿・Asiaサーバー時刻をJST換算'}
        diff = {k: v for k, v in updates.items() if e.get(k) != v}
        print(f'{name} ({english}): {START} アップデート後 → {end} {end_time} JST | {"UPDATE" if diff else "unchanged"}')
        if diff:
            e.update(diff)
            changed += 1
    missing = set(MAPPING) - matched
    if missing:
        raise RuntimeError(f'Missing expected banners: {sorted(missing)}; refusing to write')
    print(f'Mode: {"APPLY" if args.apply else "PREVIEW"}; matched={len(matched)}, changed={changed}')
    if not args.apply or not changed:
        return
    fd, tmp = tempfile.mkstemp(prefix='.events-', suffix='.json', dir=ROOT)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(tmp, EVENTS)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

if __name__ == '__main__':
    main()
