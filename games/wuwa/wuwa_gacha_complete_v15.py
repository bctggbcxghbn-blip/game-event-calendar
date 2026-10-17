#!/usr/bin/env python3
"""WuWa V15: supplement all individually named official phase-one banners.
Run after V14. Preview default, --apply to add missing banners only.
Server-time events are deliberately excluded.
"""
import argparse
import datetime as dt
import json
import os
import re
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo
import wuwa_safe_import_v13 as base

JST=ZoneInfo('Asia/Tokyo')
MAINT=re.compile(r'メンテナンス(?:日時|時間)[：:]?\s*('+base.DATE+r')\s*[~～〜－–—-]\s*('+base.DATE+r')\s*[（(]UTC\+8[）)]')

def candidates():
    _,maint=base.article(5472)
    m=MAINT.search(maint)
    if not m: raise ValueError('official maintenance time unavailable')
    start=base.parse(m.group(2),base.UTC8)
    if start is None:raise ValueError('invalid maintenance time')
    _,body=base.article(5547)
    headings=list(base.BANNER.finditer(body))
    if not headings:raise ValueError('no official banner headings found')
    found=[]
    for i,h in enumerate(headings):
        segment=body[h.end():headings[i+1].start() if i+1<len(headings) else len(body)]
        p=base.PERIOD.search(segment)
        if not p:raise ValueError('missing period for '+h.group(1))
        period=segment[p.end():p.end()+160]
        if 'アップデート後' not in period[:70]:raise ValueError('unexpected start for '+h.group(1))
        end_match=base.SINGLE.search(period)
        if not end_match or not re.search(r'[（(](?:日本標準時|JST)[）)]',period[end_match.end():end_match.end()+35]):
            raise ValueError('missing explicit JST end for '+h.group(1))
        end=base.parse(end_match.group(),base.JST)
        if end is None or start>=end:raise ValueError('invalid period for '+h.group(1))
        found.append(base.make_entry(5547,'gacha',h.group(1).strip(),start,end,'planned maintenance end + explicit JST',planned=True))
    if len(found)<4:raise ValueError(f'expected 4 banners in article 5547, found {len(found)}; aborting')
    if len({x['name'] for x in found})!=len(found):raise ValueError('duplicate banner names in source')
    return found

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--apply',action='store_true')
    p.add_argument('--events',default='events.json')
    args=p.parse_args()
    path=Path(args.events)
    existing=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(existing,list) or not all(isinstance(e,dict) for e in existing):
        raise SystemExit('events.json must be an array of objects')
    print('WUWA V15 ALL FOUR GACHA BANNERS /', 'APPLY' if args.apply else 'PREVIEW')
    print('Start is PLANNED from maintenance end. Official JST end is explicit.')
    try: entries=candidates()
    except Exception as exc:raise SystemExit('ABORT: '+str(exc))
    now=dt.datetime.now(JST)
    present={(str(e.get('game','')).lower(),str(e.get('kind','')).lower(),str(e.get('name','')).replace('（開始予定）','').strip(),str(e.get('start','')),str(e.get('end',''))) for e in existing}
    ids={e.get('id') for e in existing}
    additions=[]
    for e in entries:
        k=(e['game'],e['kind'],e['name'].replace('（開始予定）',''),e['start'],e['end'])
        if e['id'] in ids or k in present: status='EXISTS'
        elif dt.datetime.fromisoformat(e['end']+'T'+e['end_time']).replace(tzinfo=JST)<now:status='EXPIRED'
        else:status='NEW';additions.append(e)
        print(status, e['name'],e['start'],e['start_time'],'->',e['end'],e['end_time'],'JST')
    print('FOUND:',len(entries),'NEW:',len(additions),'EXISTING:',len(existing))
    if not args.apply:
        print('PREVIEW ONLY; events.json unchanged');return
    if not additions:
        print('NO CHANGES');return
    output=json.dumps(existing+additions,ensure_ascii=False,indent=2)+'\n'
    fd,tmp=tempfile.mkstemp(prefix='.wuwa-v15-',suffix='.tmp',dir=str(path.resolve().parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(output)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print('APPLIED:',len(additions),'new banners; existing entries preserved')

if __name__=='__main__':main()
