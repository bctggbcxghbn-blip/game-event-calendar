#!/usr/bin/env python3
"""WuWa V13: conservative official JP importer. Preview by default.
Only explicit JST/UTC+8 windows; gacha update-start is flagged as planned.
Never treats 'server time' as a known timezone.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/jp/article/'
SITE = 'https://wutheringwaves.kurogames.com/jp/main/news/detail/'
JST = ZoneInfo('Asia/Tokyo')
UTC8 = dt.timezone(dt.timedelta(hours=8))
DATE = r'20\d{2}年\d{1,2}月\d{1,2}日\d{1,2}[:：時]\d{2}'
PAIR = re.compile(r'('+DATE+r')\s*[~～〜－–—-]\s*('+DATE+r')')
SINGLE = re.compile(DATE)
PERIOD = re.compile(r'✦\s*開催期間\s*✦?\s*[:：]?')
BANNER = re.compile(r'(?:共鳴者集音|武器集音)[（(]イベント[）)]\s*[「『]([^」』]+)[」』]')
WEB = re.compile(r'(?:WEBイベント|H5ウェブイベント|ウェブイベント)\s*[「『]([^」』]+)[」』]')

def fetch(aid):
    req = urllib.request.Request(BASE + str(aid) + '.json', headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)

def clean(value):
    s = html.unescape(str(value or ''))
    s = re.sub(r'<(?:br|/p|/div|/li|/h[1-6])\b[^>]*>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]*>', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def parse(value, tz):
    try:
        return dt.datetime(*map(int, re.findall(r'\d+', value)[:5]), tzinfo=tz).astimezone(JST)
    except (TypeError, ValueError):
        return None

def article(aid):
    d = fetch(aid)
    return clean(d.get('articleTitle')), clean(d.get('articleContent'))

def nearest_heading(body, pos, pattern, max_distance=420):
    matches = list(pattern.finditer(body[:pos]))
    if not matches or pos-matches[-1].end()>max_distance:
        return None
    return matches[-1].group(1).strip()

def make_entry(aid, kind, name, start, end, basis, planned=False):
    identity = f'{aid}|{kind}|{name}|{start.isoformat()}|{end.isoformat()}'
    token = hashlib.sha256(identity.encode()).hexdigest()[:16]
    return {'id': 'wuwa-v13-'+token, 'game':'wuwa', 'name':name + ('（開始予定）' if planned else ''),
            'start':start.date().isoformat(), 'end':end.date().isoformat(), 'kind':kind,
            'source_status':'公式（開始予定時刻）' if planned else '公式',
            'official_url':SITE+str(aid), 'start_time':start.strftime('%H:%M'),
            'end_time':end.strftime('%H:%M'), 'time_zone':'Asia/Tokyo'}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true')
    p.add_argument('--events', default='events.json')
    args = p.parse_args()
    now = dt.datetime.now(JST)
    entries=[]
    print('WUWA V13 SAFE IMPORT', 'APPLY' if args.apply else 'PREVIEW / READ ONLY')
    print('Only explicit JST or UTC+8; server-time events are HELD.')

    # Version 3.7 maintenance notice: used only to establish planned banner start.
    planned_start=None
    try:
        title, body = article(5472)
        m = re.search(r'メンテナンス(?:日時|時間)[：:]?\s*('+DATE+r')\s*[~～〜－–—-]\s*('+DATE+r')\s*[（(]UTC\+8[）)]',body)
        if m:
            a,b = parse(m.group(1),UTC8),parse(m.group(2),UTC8)
            if a and b and a < b and (b-a).total_seconds() <= 86400:
                planned_start=b
                print('MAINTENANCE 3.7:',a.isoformat(),'->',b.isoformat(),'(official planned)')
                if b>=now:
                    entries.append(make_entry(5472,'maintenance','Ver.3.7 メンテナンス（予定）',a,b,'UTC+8'))
        else:
            print('HOLD: maintenance window not parsed')
    except Exception as e:
        print('FETCH ERROR maintenance:',type(e).__name__,str(e)[:100])

    # Phase-one banner article: each banner has its own name and explicit JST end.
    try:
        title,body=article(5547)
        for label in PERIOD.finditer(body):
            following=body[label.end():label.end()+180]
            if 'アップデート後' not in following[:70]:
                continue
            m=SINGLE.search(following)
            zone=re.search(r'[（(](日本標準時|JST)[）)]',following[:m.end()+30] if m else '')
            name=nearest_heading(body,label.start(),BANNER)
            if not (m and zone and name and planned_start):
                print('HOLD gacha section:',name or 'unknown','(missing name/JST/maintenance)');continue
            end=parse(m.group(0),JST)
            if end and end>=now and planned_start<end:
                entries.append(make_entry(5547,'gacha',name,planned_start,end,'JST end + planned maintenance end',planned=True))
    except Exception as e:
        print('FETCH ERROR gacha:',type(e).__name__,str(e)[:100])

    # Explicit UTC+8 web events. Other sections of these articles use server time: excluded.
    for aid in (5570,5356,5108):
        try:
            title,body=article(aid)
            for m in PAIR.finditer(body):
                suffix=body[m.end():m.end()+32]
                if not re.match(r'\s*[（(]UTC\+8[）)]',suffix):
                    continue
                # Name must be an explicit web-event heading immediately preceding the period.
                name=nearest_heading(body,m.start(),WEB,480)
                if not name:
                    print('HOLD unnamed UTC+8 period article',aid);continue
                a,b=parse(m.group(1),UTC8),parse(m.group(2),UTC8)
                if a and b and a<b and (b-a).days<=90 and b>=now:
                    entries.append(make_entry(aid,'event',name,a,b,'explicit UTC+8'))
        except Exception as e:
            print('FETCH ERROR content',aid,type(e).__name__,str(e)[:100])
    dedup={e['id']:e for e in entries}
    entries=list(dedup.values())
    for e in entries:
        print('FOUND:',e['kind'],e['name'],e['start'],e['start_time'],'->',e['end'],e['end_time'],'JST',e['official_url'])
    print('SAFE CANDIDATES:',len(entries),'BY KIND:',{k:sum(e['kind']==k for e in entries) for k in ('event','gacha','maintenance','challenge')})
    if not args.apply:
        print('PREVIEW ONLY. events.json unchanged.');return
    path=Path(args.events)
    existing=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(existing,list):raise ValueError('events.json must be an array')
    index={e.get('id'):i for i,e in enumerate(existing) if isinstance(e,dict)}
    added=updated=0
    for e in entries:
        if e['id'] in index:
            if existing[index[e['id']]]!=e:
                existing[index[e['id']]]=e;updated+=1
        else:
            existing.append(e);added+=1
    if added or updated:
        path.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ADDED:',added,'UPDATED:',updated)

if __name__=='__main__':main()
