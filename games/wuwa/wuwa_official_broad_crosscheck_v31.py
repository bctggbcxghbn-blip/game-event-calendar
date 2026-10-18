#!/usr/bin/env python3
"""V31: read-only expanded official-news source crosscheck for planned gacha starts.
Requires V24/V26/V27/V28/V29/V30 in games/wuwa. Does not modify events.json.
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
import wuwa_official_start_crosscheck_v30 as v30

JST = dt.timezone(dt.timedelta(hours=9))
SOURCE_HINT = re.compile(r'集音|ピックアップ|イベント|バージョン|Ver\.?|アップデート|お知らせ|開催|紹介|予告|コンテンツ|活動|ガイド|共鳴者|武器', re.I)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--events', default='events.json')
    ap.add_argument('--days-back', type=int, default=180)
    ap.add_argument('--source-limit', type=int, default=100)
    ap.add_argument('--gacha-limit', type=int, default=50)
    args = ap.parse_args()
    events = json.loads(Path(args.events).read_text(encoding='utf-8-sig'))
    if not isinstance(events, list) or any(not isinstance(x, dict) for x in events):
        raise SystemExit('ERROR: events.json must be an array of objects')
    print('WUWA V31 EXPANDED OFFICIAL NEWS CROSSCHECK / READ ONLY')
    print('Never writes events.json; maintenance estimates are never confirmed starts.')
    print('EXISTING_EVENTS:', len(events))
    items = v26.discover(args.days_back)
    maintenance = v26.maintenance_map(items)
    gacha = [x for x in items if re.search(r'集音|ピックアップ', x['title'])][:max(0,args.gacha_limit)]
    source_candidates = [x for x in items if SOURCE_HINT.search(x['title'])][:max(0,args.source_limit)]
    # Always include gacha primary articles in fetched pool, regardless of source-limit.
    pool = {x['id']: x for x in source_candidates + gacha}
    print('GACHA_ARTICLES:', len(gacha), 'OTHER_SOURCE_CANDIDATES:', len(source_candidates), 'TOTAL_TO_FETCH:', len(pool))
    bodies = {}
    fetch_errors = 0
    for item in pool.values():
        try:
            bodies[item['id']] = v26.body(item['id'])
        except Exception as exc:
            fetch_errors += 1
            print('FETCH_ERROR:', item['id'], type(exc).__name__, str(exc)[:100])
    sources = [x for x in pool.values() if x['id'] in bodies]
    stats = dict(PLANNED=0, CONFIRMED=0, HOLD_NO_EXPLICIT_JST=0, EXPIRED=0, DUPLICATE=0, REVIEW_CANDIDATE=0, PARSE_ERRORS=0, FETCH_ERRORS=fetch_errors)
    now = dt.datetime.now(JST)
    for item in gacha:
        if item['id'] not in bodies:
            continue
        try:
            records, _ = v28.extract(item, bodies[item['id']], maintenance)
        except Exception as exc:
            stats['PARSE_ERRORS'] += 1
            print('PARSE_ERROR:', item['id'], type(exc).__name__, str(exc)[:100])
            continue
        for rec in records:
            if rec.get('status') != 'PARSED_PLANNED':
                continue
            stats['PLANNED'] += 1
            label = f"{item['id']} {rec['type']} {rec['banner']} | {rec['featured']}"
            found = v30.independent_confirmation(rec, item['id'], sources, bodies)
            if not found:
                stats['HOLD_NO_EXPLICIT_JST'] += 1
                print('HOLD NO_INDEPENDENT_EXPLICIT_JST', label)
                continue
            start, refs = found
            checked = dict(rec, status='PARSED', basis='EXPLICIT_JST', start_jst=start.isoformat(timespec='minutes'))
            stats['CONFIRMED'] += 1
            print('CONFIRMED_EXPLICIT_JST', label, 'START=', checked['start_jst'], 'SOURCE_ARTICLES=', ','.join(map(str, refs)))
            ok, reason = v29.eligible(checked, now)
            if not ok:
                stats['EXPIRED'] += 1
                print('HOLD', reason, label)
                continue
            entry = v29.make_record(item, checked)
            if v29.duplicate(entry | {'banner':rec['banner'], 'featured':rec['featured']}, events):
                stats['DUPLICATE'] += 1
                print('HOLD POSSIBLE_DUPLICATE', label)
                continue
            stats['REVIEW_CANDIDATE'] += 1
            print('REVIEW_CANDIDATE', label, checked['start_jst'], '->', checked['end_jst'])
    print('SUMMARY:', ' '.join(f'{k}={v}' for k,v in stats.items()), 'READ_ONLY=true')
    print('NOTE: Only explicitly JST-labeled ranges from independent official articles count; no automatic import.')

if __name__ == '__main__':
    main()
