#!/usr/bin/env python3
"""WuWa V11: conservative article-section event pairing (read-only)."""
import argparse
import datetime as dt
import re
from wuwa_event_pair_probe_v10 import BASE, LABEL, RANGE, clean, fetch, parsedate, HEADING

# These are verified from the official article's adjacent heading and description.
# Never use them for other articles or other date ranges.
VERIFIED = {
 ('5570','2026-10-29 04:00','2026-11-11 03:59'): '潮騒探検・玄方地界',
 ('5570','2026-10-22 10:00','2026-11-11 03:59'): '傍らに響く雨音のプレゼント',
 ('5108','2026-08-06 04:00','2026-08-19 03:59'): 'ブブ企画・旅立',
 ('5108','2026-07-30 10:00','2026-08-13 10:00'): '秘玉帰巣記',
}

def resolve_name(aid, before, start, end):
    key = (str(aid), start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M'))
    if key in VERIFIED:
        name = VERIFIED[key]
        if name in before[-600:]:
            return name, 'verified nearby heading'
        return None, 'review: expected heading not found in section'
    # Only headings near the label: avoids accidentally taking another event's heading.
    matches = list(HEADING.finditer(before[-600:]))
    if matches:
        return matches[-1].group('name').strip(), 'explicit heading'
    return None, 'review: no matching heading'

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--article-ids', nargs='+', default=['5570','5356','5108'])
    args = p.parse_args()
    print('WUWA V11 NAME + TIMEZONE AUDIT / READ ONLY / events.json unchanged')
    print('Server time is not assumed to be JST; only explicit UTC+8 is converted.')
    total = named = pending_zone = eligible = 0
    for aid in args.article_ids:
        data = fetch(aid)
        body = clean(data.get('articleContent'))
        labels = list(LABEL.finditer(body))
        section_start = 0
        print('\nARTICLE', aid, clean(data.get('articleTitle')))
        for i, label in enumerate(labels):
            next_pos = labels[i+1].start() if i+1 < len(labels) else len(body)
            before = body[section_start:label.start()]
            after = body[label.end():next_pos].lstrip()
            m = RANGE.match(after[:180])
            if not m:
                section_start = label.end()
                continue
            start, end = parsedate(m.group(1)), parsedate(m.group(2))
            if not start or not end or end <= start or (end-start).days > 120:
                section_start = label.end()
                continue
            name, method = resolve_name(aid, before, start, end)
            suffix = after[m.end():m.end()+75]
            zone = 'UTC+8' if 'UTC+8' in suffix else ('server-time' if 'サーバー時間' in suffix else 'unknown')
            if zone == 'UTC+8':
                start_jst = start + dt.timedelta(hours=1)
                end_jst = end + dt.timedelta(hours=1)
                shown = f'{start_jst:%Y-%m-%d %H:%M} -> {end_jst:%Y-%m-%d %H:%M} JST'
            else:
                shown = f'{start:%Y-%m-%d %H:%M} -> {end:%Y-%m-%d %H:%M} ({zone}, NOT CONVERTED)'
                pending_zone += 1
            total += 1
            named += bool(name)
            # Eligible for safe JST registration only when explicit timezone + verified name + not ended.
            safe = bool(name) and zone == 'UTC+8' and end_jst >= dt.datetime.now()
            eligible += safe
            print(f'  PAIR: {name or "REVIEW NAME"} | {shown} | {method} | {"SAFE_JST_CANDIDATE" if safe else "HOLD"}')
            if not name:
                print('    NEARBY:', before[-160:].replace('\n',' '))
            section_start = label.end()
    print(f'\nSUMMARY: periods={total} named={named} review_name={total-named} timezone_unverified={pending_zone} safe_jst_candidates={eligible}')
    print('READ ONLY. Server-time entries are never auto-registered by this script.')

if __name__ == '__main__':
    main()
