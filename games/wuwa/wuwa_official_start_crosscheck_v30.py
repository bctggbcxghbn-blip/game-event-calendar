#!/usr/bin/env python3
"""V30: read-only independent official confirmation for planned gacha starts.

Requires V24, V26, V27, V28, V29 in the same games/wuwa directory.
Never infers an actual start from a maintenance plan. Never edits events.json.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wuwa_dynamic_gacha_preview_v26 as v26
import wuwa_dynamic_gacha_preview_v28 as v28
import wuwa_dynamic_gacha_import_v29 as v29

JST = dt.timezone(dt.timedelta(hours=9))
# This is deliberately strict: dates must appear together in a JST-labeled range.
DATE = r'20\d{2}年\s*\d{1,2}月\s*\d{1,2}日\s*\d{1,2}[:：時]\d{2}'
RANGE = re.compile(r'('+DATE+r')\s*[~～〜－–—-]\s*('+DATE+r')\s*[（(]\s*(?:日本標準時|JST)\s*[）)]')

def explicit_ranges(content):
    for m in RANGE.finditer(content):
        try:
            a = v26.dateparse(m.group(1), JST)
            b = v26.dateparse(m.group(2), JST)
            if a < b:
                yield a, b, m.start()
        except ValueError:
            continue

def independent_confirmation(rec, primary_id, items, bodies, max_lookback=800):
    """Return independent explicit-JST range or None.

    A different official article must name the *exact banner* near the range,
    and the independently stated end must equal the primary end.
    A mere mention elsewhere in a news article is not enough.
    """
    banner = rec.get('banner', '')
    if not banner or banner == '?':
        return None
    try:
        expected_end = dt.datetime.fromisoformat(rec['end_jst'])
    except (ValueError, KeyError):
        return None
    matches = []
    for item in items:
        if item['id'] == primary_id:
            continue
        content = bodies.get(item['id'], '')
        if not content or banner not in (item['title'] + content):
            continue
        for start, end, pos in explicit_ranges(content):
            if end != expected_end:
                continue
            # Require the exact banner close to the date, not anywhere in article.
            context = content[max(0, pos-max_lookback):pos+120]
            if banner not in context and banner not in item['title']:
                continue
            matches.append((start, item['id']))
    # Conflicting explicit official starts are held for manual review.
    starts = {x[0] for x in matches}
    if len(starts) != 1:
        return None
    start = next(iter(starts))
    return start, sorted({x[1] for x in matches})

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--events', default='events.json')
    p.add_argument('--days-back', type=int, default=120)
    p.add_argument('--limit', type=int, default=60)
    args = p.parse_args()
    events = json.loads(Path(args.events).read_text(encoding='utf-8-sig'))
    if not isinstance(events, list) or any(not isinstance(e, dict) for e in events):
        raise SystemExit('ERROR: events.json must be an array of objects')
    print('WUWA V30 OFFICIAL START CROSSCHECK / READ ONLY')
    print('No --apply. No events.json writes. No maintenance-time promotion.')
    print('EXISTING_EVENTS:', len(events))
    items = v26.discover(args.days_back)
    maintenance = v26.maintenance_map(items)
    gachas = [x for x in items if re.search(r'集音|ピックアップ', x['title'])][:max(0,args.limit)]
    # Check other official gacha articles as independent confirmation sources.
    bodies = {}
    errors = 0
    for item in gachas:
        try:
            bodies[item['id']] = v26.body(item['id'])
        except Exception as exc:
            print('FETCH_ERROR:', item['id'], type(exc).__name__, str(exc)[:120])
            errors += 1
    stats = dict(PLANNED=0, CONFIRMED=0, HOLD_NO_INDEPENDENT_JST=0,
                 HOLD_EXPIRED=0, HOLD_DUPLICATE=0, REVIEW_CANDIDATE=0, FETCH_ERRORS=errors)
    now = dt.datetime.now(JST)
    for item in gachas:
        if item['id'] not in bodies:
            continue
        try:
            records, _ = v28.extract(item, bodies[item['id']], maintenance)
        except Exception as exc:
            print('PARSE_ERROR:', item['id'], type(exc).__name__, str(exc)[:120])
            stats['FETCH_ERRORS'] += 1
            continue
        for rec in records:
            if rec.get('status') != 'PARSED_PLANNED':
                continue
            stats['PLANNED'] += 1
            label = f"{item['id']} {rec['type']} {rec['banner']} {rec['featured']}"
            result = independent_confirmation(rec, item['id'], gachas, bodies)
            if result is None:
                print('HOLD NO_INDEPENDENT_EXPLICIT_JST', label)
                stats['HOLD_NO_INDEPENDENT_JST'] += 1
                continue
            start, refs = result
            # Only the *independently explicit* start is now used.
            checked = dict(rec, status='PARSED', basis='EXPLICIT_JST', start_jst=start.isoformat(timespec='minutes'))
            stats['CONFIRMED'] += 1
            print('CONFIRMED_EXPLICIT_JST', label, 'START=', checked['start_jst'], 'SOURCE_ARTICLES=', ','.join(refs))
            ok, reason = v29.eligible(checked, now)
            if not ok:
                print('HOLD', reason, label)
                stats['HOLD_EXPIRED'] += 1
                continue
            entry = v29.make_record(item, checked)
            if v29.duplicate(entry | {'banner': rec['banner'], 'featured': rec['featured']}, events):
                print('HOLD POSSIBLE_DUPLICATE', label)
                stats['HOLD_DUPLICATE'] += 1
                continue
            print('REVIEW_CANDIDATE', label, checked['start_jst'], '->', checked['end_jst'])
            stats['REVIEW_CANDIDATE'] += 1
    print('SUMMARY:', ' '.join(f'{k}={v}' for k,v in stats.items()), 'READ_ONLY=true')
    print('NEXT: inspect confirmed source articles before any importer change.')

if __name__ == '__main__':
    main()
