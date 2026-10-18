#!/usr/bin/env python3
"""V27 safe preview: improved official gacha extraction, no file writes.
Requires V24 and V26 alongside this script in games/wuwa/.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wuwa_dynamic_gacha_preview_v26 as v26
import wuwa_official_discovery_v24 as discovery

# Anchor to heading start; exclude repeated mentions in descriptions.
HEADING = re.compile(r'(共鳴者集音|武器集音)\s*[（(](?:イベント|追憶)[）)]\s*(?:[—–\-]+\s*)?[「『]([^」』]+)[」』]')
PERIOD = re.compile(r'✦\s*開催期間\s*✦?\s*[:：]?')

def parse(item, content, maintenance):
    # Some individual announcements put banner name in the article title, not body.
    found = list(HEADING.finditer(content))
    sections = []
    if found:
        for i, m in enumerate(found):
            following = content[m.end(): found[i+1].start() if i+1 < len(found) else len(content)]
            # Repeated heading mentions in descriptive text do not contain an immediate period.
            if not PERIOD.search(following[:600]):
                continue
            sections.append((m.group(1), m.group(2), following))
    else:
        m = HEADING.search(item['title'])
        if m and PERIOD.search(content[:650]):
            sections.append((m.group(1), m.group(2), content))
    out = []
    seen = set()
    for kind, name, chunk in sections:
        # V26 parser handles time-zone validation and planned maintenance start.
        synthetic = f'{kind}（イベント）「{name}」 ' + chunk
        records, _ = v26.parse_banners(item, synthetic, maintenance)
        if not records:
            continue
        r = records[0]
        key = (r['type'], r['banner'], r.get('start_jst'), r.get('end_jst'))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days-back', type=int, default=120)
    ap.add_argument('--limit', type=int, default=30)
    ap.add_argument('--events', default='events.json')
    args = ap.parse_args()
    print('WUWA V27 GACHA EXTRACTION / READ ONLY')
    print('Never writes events.json. Planned starts are estimates, not confirmed start times.')
    items = v26.discover(args.days_back)
    maintenance = v26.maintenance_map(items)
    gachas = [x for x in items if re.search(r'集音|ピックアップ', x['title'])]
    try:
        events = json.loads(Path(args.events).read_text(encoding='utf-8'))
        if not isinstance(events, list):
            raise ValueError('events.json is not a list')
    except Exception as exc:
        print('ERROR: Cannot read existing events safely:', exc)
        raise SystemExit(1)
    print('ARTICLES:', len(gachas), 'INSPECTING:', min(len(gachas), max(0, args.limit)), 'EXISTING_EVENTS:', len(events))
    counts = {'PARSED':0,'PARSED_PLANNED':0,'HOLD':0,'POSSIBLE_DUPLICATE':0}
    for item in gachas[:max(0,args.limit)]:
        print('\nARTICLE:', item['id'], item['title'])
        try:
            content = v26.body(item['id'])
            if not content:
                print('HOLD BODY_EMPTY'); counts['HOLD'] += 1; continue
            records = parse(item, content, maintenance)
            if not records:
                print('HOLD NO_VALID_SECTION'); counts['HOLD'] += 1; continue
            for r in records:
                counts[r['status']] += 1
                if r['status'] == 'HOLD':
                    print('HOLD', r['type'], r['banner'], r.get('reason','UNKNOWN')); continue
                # Advisory matching: existing schemas may vary; do not claim zero means safe to import.
                name = r['banner']; feat = r['featured']
                possible = [e for e in events if isinstance(e,dict) and e.get('game')=='wuwa'
                            and (name in str(e.get('name','')) or (feat != '?' and feat in str(e.get('name',''))))]
                if possible: counts['POSSIBLE_DUPLICATE'] += 1
                print(r['status'], r['type'], name, '|', feat, '|', r['start_jst'], '->', r['end_jst'], '|',r['basis'], '| NAME_MATCHES=',len(possible))
        except Exception as exc:
            print('ARTICLE_ERROR', type(exc).__name__, str(exc)[:160]); counts['HOLD'] += 1
    print('\nSUMMARY:', ' '.join(k+'='+str(v) for k,v in counts.items()), 'READ_ONLY=true')
    print('No import until duplicate detection and planned maintenance timing are reviewed.')

if __name__=='__main__':
    main()
