#!/usr/bin/env python3
"""V28 read-only: individual announcement recovery and conservative import readiness.
Requires V24, V26 and V27 in games/wuwa/. Never writes events.json.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wuwa_dynamic_gacha_preview_v26 as v26
import wuwa_dynamic_gacha_preview_v27 as v27

JST = dt.timezone(dt.timedelta(hours=9))

def extract(item, content, maintenance):
    records = v27.parse(item, content, maintenance)
    if records:
        return records, 'V27'
    # Individual articles often put the only heading in their title, while body
    # starts immediately with "イベント期間中...". Rebuild a single section.
    heading = v27.HEADING.search(item['title'])
    if not heading or not v27.PERIOD.search(content[:1200]):
        return [], 'NO_VALID_SECTION'
    kind, name = heading.group(1), heading.group(2)
    synthetic = f'{kind}（イベント）「{name}」\n{content}'
    candidates, _ = v26.parse_banners(item, synthetic, maintenance)
    return candidates[:1], 'TITLE_FALLBACK'

def normalized(text):
    return re.sub(r'[\s　「」『』（）()・:：—－-]', '', str(text or '')).casefold()

def match_existing(record, events):
    banner = normalized(record['banner'])
    featured = normalized(record['featured']) if record['featured'] != '?' else ''
    matches = []
    for idx, ev in enumerate(events):
        if not isinstance(ev, dict) or ev.get('game') != 'wuwa':
            continue
        label = normalized(' '.join(str(ev.get(k, '')) for k in ('name', 'title', 'banner', 'character', 'weapon')))
        if (banner and banner in label) or (featured and featured in label):
            matches.append(idx)
    return matches

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days-back', type=int, default=120)
    ap.add_argument('--limit', type=int, default=30)
    ap.add_argument('--events', default='events.json')
    args = ap.parse_args()
    print('WUWA V28 DYNAMIC GACHA IMPORT READINESS / READ ONLY')
    print('No --apply. No changes to events.json. Planned starts are NEVER eligible.')
    events_path = Path(args.events)
    try:
        events = json.loads(events_path.read_text(encoding='utf-8'))
        if not isinstance(events, list) or any(not isinstance(x, dict) for x in events):
            raise ValueError('Expected list of event objects')
    except Exception as exc:
        raise SystemExit('ERROR reading events.json: '+str(exc))
    print('EXISTING_EVENTS:', len(events))
    if events:
        print('SCHEMA_SAMPLE_KEYS:', ','.join(sorted(events[0].keys())))
        for ev in events:
            if ev.get('game') == 'wuwa':
                print('WUWA_SAMPLE_KEYS:', ','.join(sorted(ev.keys())))
                print('WUWA_SAMPLE_FIELDS:', json.dumps({k:ev.get(k) for k in ('id','name','kind','type','start','end','start_time','end_time','source') if k in ev}, ensure_ascii=False)[:900])
                break
    items = v26.discover(args.days_back)
    maintenance = v26.maintenance_map(items)
    gachas = [x for x in items if re.search(r'集音|ピックアップ', x['title'])]
    stats = {'EXPLICIT':0,'PLANNED_HOLD':0,'UNPARSED_HOLD':0,'DUPLICATE_HOLD':0,'EXPIRED_HOLD':0,'REVIEW_CANDIDATE':0}
    today = dt.datetime.now(JST)
    for item in gachas[:max(0,args.limit)]:
        print('\nARTICLE:', item['id'], item['title'])
        try:
            content = v26.body(item['id'])
            if not content:
                print('HOLD BODY_EMPTY'); stats['UNPARSED_HOLD']+=1; continue
            records, method = extract(item, content, maintenance)
            if not records:
                print('HOLD NO_VALID_SECTION'); stats['UNPARSED_HOLD']+=1; continue
            for rec in records:
                label = rec['type']+' '+rec['banner']+' | '+rec['featured']
                if rec['status'] == 'PARSED_PLANNED':
                    print('HOLD PLANNED_START', label, '|', method)
                    stats['PLANNED_HOLD']+=1; continue
                if rec['status'] != 'PARSED':
                    print('HOLD', rec.get('reason','UNPARSED'), label, '|', method)
                    stats['UNPARSED_HOLD']+=1; continue
                stats['EXPLICIT']+=1
                matches = match_existing(rec, events)
                end = dt.datetime.fromisoformat(rec['end_jst'])
                if matches:
                    print('HOLD POSSIBLE_DUPLICATE', label, '| MATCH_INDICES=',','.join(map(str,matches[:8])))
                    stats['DUPLICATE_HOLD']+=1
                elif end < today:
                    print('HOLD EXPIRED', label, '| END=',rec['end_jst'])
                    stats['EXPIRED_HOLD']+=1
                else:
                    print('REVIEW_CANDIDATE',label,'|',rec['start_jst'],'->',rec['end_jst'],'| ARTICLE=',item['id'],'| METHOD=',method)
                    stats['REVIEW_CANDIDATE']+=1
        except Exception as exc:
            print('HOLD ARTICLE_ERROR',type(exc).__name__,str(exc)[:140]);stats['UNPARSED_HOLD']+=1
    print('\nSUMMARY:', ' '.join(k+'='+str(v) for k,v in stats.items()),'READ_ONLY=true')
    print('NEXT: review candidate records and schema before building any apply mode.')

if __name__ == '__main__':
    main()
