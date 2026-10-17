#!/usr/bin/env python3
"""WuWa V20: import official SERVER-CALENDAR dates without claiming JST.
Requires wuwa_server_date_preview_v19.py and wuwa_safe_import_v13.py.
Default preview; --apply adds missing entries only. Does not alter existing entries.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path
import wuwa_server_date_preview_v19 as v19
import wuwa_safe_import_v13 as v13

PATH = Path('events.json')


def extract():
    title, body = v13.article(v19.ARTICLE_ID)
    result = []
    for name in v19.TARGETS:
        matches = []
        for h in re.finditer(r'[「『]' + re.escape(name) + r'[」』]', body):
            period = v19.PERIOD.search(body, h.end(), h.end() + 650)
            if not period:
                continue
            between = body[h.end():period.start()]
            if re.search(r'(?:イベント|ログインボーナス)[^。✦]{0,45}[「『][^」』]+[」』]', between):
                continue
            raw_a, raw_b = period.group(1), period.group(7)
            try:
                a = dt.datetime(*map(int, re.findall(r'\d+', raw_a))).date()
                b = dt.datetime(*map(int, re.findall(r'\d+', raw_b))).date()
            except (ValueError, TypeError):
                continue
            if a <= b:
                matches.append((a.isoformat(), b.isoformat()))
        matches = sorted(set(matches))
        if len(matches) != 1:
            raise ValueError(f'{name}: expected one unambiguous server-time period; found {len(matches)}')
        start, end = matches[0]
        result.append({
            'id': 'wuwa-serverdate-' + str(v19.ARTICLE_ID) + '-' + str(v19.TARGETS.index(name)+1),
            'game': 'wuwa', 'name': name, 'start': start, 'end': end,
            'kind': 'event',
            'source_status': '公式（サーバー日付のみ・日本時間未確認）',
            'time_zone': 'server (unverified)',
            'official_url': v13.SITE + str(v19.ARTICLE_ID),
        })
    return title, result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    print('WUWA V20 SERVER-DATE IMPORT /', 'APPLY' if args.apply else 'PREVIEW')
    print('These are SERVER calendar dates, NOT JST. No start_time/end_time fields.')
    if not PATH.is_file():
        raise SystemExit('ERROR: events.json missing')
    events = json.loads(PATH.read_text(encoding='utf-8-sig'))
    if not isinstance(events, list) or not all(isinstance(e, dict) for e in events):
        raise SystemExit('ERROR: events.json must be an array of objects')
    title, candidates = extract()
    print('SOURCE:', title)
    existing_ids = {str(e.get('id', '')) for e in events}
    new = []
    for c in candidates:
        # A same-name WuWa event is held for review if dates/metadata differ.
        same = [e for e in events if str(e.get('game','')).lower() == 'wuwa' and str(e.get('name','')).strip() == c['name']]
        if same:
            if any(e.get('start') == c['start'] and e.get('end') == c['end'] for e in same):
                print('EXISTS:', c['name'], c['start'], c['end'])
                continue
            print('HOLD CONFLICT:', c['name'], 'existing event has different dates; no overwrite')
            continue
        if c['id'] in existing_ids:
            print('HOLD ID COLLISION:', c['name'])
            continue
        print('NEW SERVER-DATE:', c['name'], c['start'], '->', c['end'])
        new.append(c)
    print(f'SUMMARY: extracted={len(candidates)} new={len(new)} existing_total={len(events)}')
    if not args.apply:
        print('PREVIEW ONLY. events.json unchanged. To add, run with --apply.')
        return
    if not new:
        print('APPLIED: 0 new events; no changes needed')
        return
    updated = events + new
    # Only write after full extraction and validation; atomic replace.
    tmp = PATH.with_name(PATH.name + '.wuwa-v20.tmp')
    try:
        tmp.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        tmp.replace(PATH)
    finally:
        if tmp.exists():
            tmp.unlink()
    print(f'APPLIED: {len(new)} new server-date-only events; existing entries preserved')
    print('WARNING: server dates are not verified as Japan-local calendar dates.')


if __name__ == '__main__':
    main()
