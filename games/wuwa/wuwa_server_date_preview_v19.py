#!/usr/bin/env python3
"""WuWa V19: read-only, date-only preview of official server-time events.
No timezone conversion; no events.json writes. Requires wuwa_safe_import_v13.py.
"""
import datetime as dt
import json
import re
from pathlib import Path
import wuwa_safe_import_v13 as v13

ARTICLE_ID = 5570
TARGETS = (
    '天工の探し物',
    '無音イレイサー',
    '潮騒探検・玄方地界',
    '傍らに響く雨音のプレゼント',
)
DATE = r'(20\d{2})年(\d{1,2})月(\d{1,2})日(\d{1,2})[:：](\d{2})'
PERIOD = re.compile(r'✦\s*開催期間\s*[：:]?\s*('+DATE+r')\s*[~～〜－–—-]\s*('+DATE+r')\s*[（(]サーバー時間[）)]')


def main():
    print('WUWA V19 SERVER-TIME DATE-ONLY PREVIEW / READ ONLY')
    print('Dates are official SERVER CALENDAR dates, NOT converted to JST.')
    print('No start_time/end_time; no Asia/Tokyo claim; events.json unchanged.')
    path = Path('events.json')
    if not path.is_file():
        raise SystemExit('ERROR: events.json not found at repository root')
    events = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise SystemExit('ERROR: events.json must be an array')
    title, body = v13.article(ARTICLE_ID)
    print('ARTICLE:', ARTICLE_ID, title)
    candidates = []
    for name in TARGETS:
        heading = re.compile(r'[「『]'+re.escape(name)+r'[」』]')
        matches = list(heading.finditer(body))
        valid = []
        for h in matches:
            next_period = PERIOD.search(body, h.end(), h.end()+650)
            if not next_period:
                continue
            # Another named event heading before this period means it belongs to that event.
            between = body[h.end():next_period.start()]
            if re.search(r'(?:イベント|ログインボーナス)[^。✦]{0,45}[「『][^」』]+[」』]', between):
                continue
            a = next_period.group(1)
            b = next_period.group(7)
            aa = list(map(int, re.findall(r'\d+', a)))
            bb = list(map(int, re.findall(r'\d+', b)))
            try:
                start = dt.date(*aa[:3]); end = dt.date(*bb[:3])
            except ValueError:
                continue
            if start <= end:
                valid.append((start, end, a, b))
        valid = list(dict.fromkeys(valid))
        if len(valid) != 1:
            print('HOLD:', name, 'matching_periods=',len(valid))
            continue
        start,end,raw_start,raw_end = valid[0]
        exists = any(str(e.get('game','')).lower()=='wuwa' and str(e.get('name','')).strip()==name and str(e.get('start',''))==start.isoformat() and str(e.get('end',''))==end.isoformat() for e in events if isinstance(e,dict))
        status = 'EXISTS' if exists else 'DATE_ONLY_CANDIDATE'
        print(f'{status}: {name} | {start} -> {end} | original {raw_start} -> {raw_end} (SERVER TIME)')
        candidates.append({'game':'wuwa','name':name,'start':start.isoformat(),'end':end.isoformat(), 'kind':'event','source_status':'公式（サーバー日付・JST未確認）','time_zone':'server (unverified)','official_url':v13.SITE+str(ARTICLE_ID)})
    print('SUMMARY: matched=',len(candidates),'expected=',len(TARGETS),'existing_events=',len(events))
    print('IMPORTANT: date-only preview does not establish Japan-local calendar boundaries.')
    print('NO APPLY MODE. events.json unchanged.')

if __name__=='__main__':
    main()
