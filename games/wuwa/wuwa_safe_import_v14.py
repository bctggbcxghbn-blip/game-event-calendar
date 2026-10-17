#!/usr/bin/env python3
"""V14 conservative WuWa importer. Reuses the verified V13 extraction.
Preview by default; --apply explicitly writes only validated, nonduplicate entries.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo
import wuwa_safe_import_v13 as v13

JST=ZoneInfo('Asia/Tokyo')

def key(e):
    name=str(e.get('name','')).replace('（開始予定）','').strip()
    return (str(e.get('game','')).lower(),str(e.get('kind','')).lower(),name,str(e.get('start','')),str(e.get('end','')))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--events',default='events.json')
    args=parser.parse_args()
    path=Path(args.events)
    if not path.is_file():
        raise SystemExit(f'ERROR: {path} not found')
    existing=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(existing,list) or not all(isinstance(x,dict) for x in existing):
        raise SystemExit('ERROR: events.json must be a list of objects')
    now=dt.datetime.now(JST)
    entries=[]
    errors=[]
    print('WUWA V14 SAFE IMPORT /', 'APPLY' if args.apply else 'PREVIEW')
    print('Explicit JST/UTC+8 only. Server-time remains excluded.')
    planned_start=None
    try:
        _,body=v13.article(5472)
        m=v13.re.search(r'メンテナンス(?:日時|時間)[：:]?\s*('+v13.DATE+r')\s*[~～〜－–—-]\s*('+v13.DATE+r')\s*[（(]UTC\+8[）)]',body)
        if m:
            a,b=v13.parse(m.group(1),v13.UTC8),v13.parse(m.group(2),v13.UTC8)
            if a and b and a<b and (b-a).total_seconds()<=86400:
                planned_start=b
                if b>=now:entries.append(v13.make_entry(5472,'maintenance','Ver.3.7 メンテナンス（予定）',a,b,'UTC+8'))
        if planned_start is None: errors.append('maintenance reference unavailable')
    except Exception as exc:errors.append(f'maintenance fetch failed: {exc}')
    try:
        _,body=v13.article(5547)
        for label in v13.PERIOD.finditer(body):
            following=body[label.end():label.end()+180]
            if 'アップデート後' not in following[:70]:continue
            m=v13.SINGLE.search(following)
            zone=v13.re.search(r'[（(](日本標準時|JST)[）)]',following[:m.end()+30] if m else '')
            name=v13.nearest_heading(body,label.start(),v13.BANNER)
            if not (m and zone and name and planned_start):continue
            end=v13.parse(m.group(0),v13.JST)
            if end and end>=now and planned_start<end:
                entries.append(v13.make_entry(5547,'gacha',name,planned_start,end,'JST + planned maintenance end',planned=True))
    except Exception as exc:errors.append(f'gacha fetch failed: {exc}')
    for aid in (5570,5356,5108):
        try:
            _,body=v13.article(aid)
            for m in v13.PAIR.finditer(body):
                if not v13.re.match(r'\s*[（(]UTC\+8[）)]',body[m.end():m.end()+32]):continue
                name=v13.nearest_heading(body,m.start(),v13.WEB,480)
                if not name:continue
                a,b=v13.parse(m.group(1),v13.UTC8),v13.parse(m.group(2),v13.UTC8)
                if a and b and a<b and (b-a).days<=90 and b>=now:
                    entries.append(v13.make_entry(aid,'event',name,a,b,'explicit UTC+8'))
        except Exception as exc:errors.append(f'content {aid} fetch failed: {exc}')
    if errors:
        for error in errors:print('ERROR:',error)
        raise SystemExit('ABORT: incomplete official data; events.json unchanged')
    candidates={e['id']:e for e in entries}
    seen_ids={e.get('id') for e in existing}
    seen_keys={key(e) for e in existing}
    to_add=[]
    for entry in candidates.values():
        if entry['id'] in seen_ids or key(entry) in seen_keys:
            print('SKIP DUPLICATE:',entry['kind'],entry['name']);continue
        to_add.append(entry)
        print('ADD CANDIDATE:',entry['kind'],entry['name'],entry['start'],entry['start_time'],'->',entry['end'],entry['end_time'],'JST')
    print('CANDIDATES:',len(candidates),'NEW:',len(to_add),'EXISTING:',len(existing))
    if not args.apply:
        print('PREVIEW ONLY. No file changes. Use --apply after reviewing output.');return
    if not to_add:
        print('NO CHANGES');return
    updated=existing+to_add
    temp=path.with_name(path.name+'.wuwa-v14.tmp')
    try:
        temp.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        temp.replace(path)
    finally:
        if temp.exists():temp.unlink()
    print('APPLIED:',len(to_add),'new events; existing entries preserved')

if __name__=='__main__':main()
