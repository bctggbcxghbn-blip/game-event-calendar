#!/usr/bin/env python3
"""V29: conservative Wuthering Waves JP official gacha importer.

Requires v24, v26, v27, v28 alongside this file. Dry-run by default.
Only explicit JST starts/ends, unexpired, deduplicated records are eligible.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wuwa_dynamic_gacha_preview_v26 as v26
import wuwa_dynamic_gacha_preview_v28 as v28

JST = dt.timezone(dt.timedelta(hours=9))

def norm(s):
    return re.sub(r'[\s　「」『』（）()・:：—－-]', '', str(s or '')).casefold()

def eligible(rec, now):
    if rec.get('status') != 'PARSED' or rec.get('basis') != 'EXPLICIT_JST':
        return False, 'NOT_EXPLICIT_JST'
    if rec.get('type') not in ('CHARACTER', 'WEAPON'):
        return False, 'INVALID_TYPE'
    if not rec.get('banner') or rec.get('featured') in ('', '?', None):
        return False, 'UNKNOWN_FEATURED'
    try:
        start = dt.datetime.fromisoformat(rec['start_jst'])
        end = dt.datetime.fromisoformat(rec['end_jst'])
    except (KeyError, ValueError, TypeError):
        return False, 'INVALID_DATES'
    if start.utcoffset() != dt.timedelta(hours=9) or end.utcoffset() != dt.timedelta(hours=9):
        return False, 'NOT_JST'
    if not start < end:
        return False, 'INVALID_RANGE'
    if end <= now:
        return False, 'EXPIRED'
    return True, 'OK'

def duplicate(rec, events):
    banner = norm(rec['banner'])
    featured = norm(rec['featured'])
    for event in events:
        if event.get('game') != 'wuwa':
            continue
        if event.get('id') == rec['id']:
            return True
        # Conservative: block matching banner/featured in any existing name/metadata.
        labels = ' '.join(str(event.get(k, '')) for k in ('name','original_name','banner','character','weapon'))
        n = norm(labels)
        if (banner and banner in n) or (featured and featured in n):
            return True
        # Same kind, same period and same gacha type: review instead of importing.
        if (event.get('kind') in ('gacha','character_gacha','weapon_gacha')
            and str(event.get('start',''))[:10] == rec['start'][:10]
            and str(event.get('end',''))[:10] == rec['end'][:10]):
            return True
    return False

def make_record(item, rec):
    key = f"{item['id']}|{rec['type']}|{rec['banner']}|{rec['featured']}"
    digest = hashlib.sha256(key.encode('utf-8')).hexdigest()[:14]
    start, end = rec['start_jst'], rec['end_jst']
    name = f"{rec['featured']}（{rec['banner']}）" if rec['type']=='CHARACTER' else f"{rec['banner']}（武器集音）"
    return {
        'id': 'wuwa-official-gacha-' + digest,
        'game': 'wuwa',
        'kind': 'gacha',
        'name': name,
        'original_name': rec['banner'],
        'start': start,
        'end': end,
        'time_zone': 'Asia/Tokyo',
        'source_status': 'official_explicit_jst',
        'official_url': 'https://wutheringwaves.kurogames.com/jp/main/news/detail/' + str(item['id']),
    }

def validate(data, original):
    if not isinstance(data, list) or len(data) < len(original):
        raise ValueError('invalid event list or event count decreased')
    if data[:len(original)] != original:
        raise ValueError('existing event records changed')
    ids = [x.get('id') for x in data if isinstance(x, dict)]
    if len(ids) != len(data) or any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError('missing or duplicate IDs')
    for e in data:
        if not isinstance(e, dict) or not all(e.get(k) for k in ('id','game','kind','name','start','end')):
            raise ValueError('invalid event schema')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Write only after all safety checks')
    ap.add_argument('--events', default='events.json')
    ap.add_argument('--days-back', type=int, default=120)
    ap.add_argument('--limit', type=int, default=30)
    args = ap.parse_args()
    print('WUWA V29 DYNAMIC GACHA IMPORT', 'MODE=APPLY' if args.apply else 'MODE=DRY_RUN')
    path = Path(args.events)
    raw = path.read_bytes()
    events = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(events, list) or any(not isinstance(x,dict) for x in events):
        raise SystemExit('ERROR: events.json must be an array of objects')
    validate(events, [])
    original = json.loads(json.dumps(events, ensure_ascii=False))
    print('EXISTING_EVENTS:', len(events))
    now = dt.datetime.now(JST)
    items = v26.discover(args.days_back)
    maintenance = v26.maintenance_map(items)
    articles = [x for x in items if re.search(r'集音|ピックアップ', x['title'])]
    stats = {'EXPLICIT':0,'PLANNED_HOLD':0,'EXPIRED_HOLD':0,'DUPLICATE_HOLD':0,'OTHER_HOLD':0,'CANDIDATE':0,'ARTICLE_ERROR':0}
    pending = []
    for item in articles[:max(0,args.limit)]:
        try:
            content = v26.body(item['id'])
            if not content:
                print('HOLD BODY_EMPTY', item['id']); stats['OTHER_HOLD']+=1; continue
            records, method = v28.extract(item, content, maintenance)
            if not records:
                print('HOLD NO_VALID_SECTION', item['id']); stats['OTHER_HOLD']+=1; continue
            for rec in records:
                label = f"{item['id']} {rec.get('type')} {rec.get('banner')} {rec.get('featured')}"
                if rec.get('status') == 'PARSED_PLANNED':
                    print('HOLD PLANNED_START', label); stats['PLANNED_HOLD']+=1; continue
                ok, reason = eligible(rec, now)
                if not ok:
                    print('HOLD', reason, label)
                    stats['EXPIRED_HOLD' if reason=='EXPIRED' else 'OTHER_HOLD']+=1
                    continue
                stats['EXPLICIT']+=1
                entry = make_record(item, rec)
                if duplicate(entry | {'banner':rec['banner'],'featured':rec['featured']}, events + pending):
                    print('HOLD POSSIBLE_DUPLICATE', label); stats['DUPLICATE_HOLD']+=1; continue
                pending.append(entry)
                stats['CANDIDATE']+=1
                print('CANDIDATE', label, rec['start_jst'], '->', rec['end_jst'])
        except Exception as exc:
            print('ARTICLE_ERROR', item['id'], type(exc).__name__, str(exc)[:180]); stats['ARTICLE_ERROR']+=1
    print('SUMMARY:', ' '.join(f'{k}={v}' for k,v in stats.items()), 'BEFORE='+str(len(events)), 'AFTER='+str(len(events)+len(pending)))
    if not args.apply:
        print('DRY_RUN_COMPLETE: events.json unchanged; use --apply to write eligible candidates')
        return
    if stats['ARTICLE_ERROR']:
        raise SystemExit('APPLY_ABORTED: article fetch/parse errors; no changes')
    if not pending:
        print('APPLY_NO_CHANGES: no eligible new gacha')
        return
    updated = events + pending
    validate(updated, original)
    # Guard against another job changing events.json since read.
    if path.read_bytes() != raw:
        raise SystemExit('APPLY_ABORTED: events.json changed during run')
    backup = path.with_name(path.name+'.v29.bak')
    shutil.copy2(path, backup)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, prefix='.wuwa-v29-', suffix='.tmp', delete=False) as f:
            temp_path = Path(f.name)
            json.dump(updated, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        check = json.loads(temp_path.read_text(encoding='utf-8'))
        validate(check, original)
        os.replace(temp_path, path)
        temp_path = None
        validate(json.loads(path.read_text(encoding='utf-8')), original)
        print('APPLY_COMPLETE:', len(pending), 'added; BACKUP:', backup)
    except Exception:
        shutil.copy2(backup, path)
        raise
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

if __name__ == '__main__':
    main()
