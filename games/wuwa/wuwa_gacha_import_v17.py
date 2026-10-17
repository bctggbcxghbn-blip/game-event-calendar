#!/usr/bin/env python3
"""WuWa V17: classify each official banner by featured 5-star item, not headings.
Preview by default. --apply only appends missing, validated records.
"""
import argparse
import datetime as dt
import json
import os
import re
import tempfile
from pathlib import Path
import wuwa_safe_import_v13 as base

JST=base.JST
MAINT=re.compile(r'メンテナンス(?:日時|時間)[：:]?\s*('+base.DATE+r')\s*[~～〜－–—-]\s*('+base.DATE+r')\s*[（(]UTC\+8[）)]')
CHAR=re.compile(r'星\s*5\s*共鳴者\s*[「『]([^」』]+)[」』]')
WEAPON=re.compile(r'星\s*5\s*武器\s*[「『]([^」』]+)[」』]')
TZ=re.compile(r'[（(](?:日本標準時|JST)[）)]')

def extract():
    _,maintenance=base.article(5472)
    m=MAINT.search(maintenance)
    if not m: raise ValueError('maintenance window not found')
    start=base.parse(m.group(2),base.UTC8)
    if not start: raise ValueError('maintenance time invalid')
    _,body=base.article(5547)
    headings=list(base.BANNER.finditer(body))
    if len(headings)!=4: raise ValueError(f'expected 4 sections, got {len(headings)}')
    entries=[]
    for i,h in enumerate(headings):
        segment=body[h.end():headings[i+1].start() if i+1<len(headings) else len(body)]
        chars=CHAR.findall(segment)
        weapons=WEAPON.findall(segment)
        if (len(chars),len(weapons)) not in ((1,0),(0,1)):
            raise ValueError(f'section {i+1} has ambiguous featured items: chars={chars}, weapons={weapons}')
        if chars:
            # Character banner title is explicit in this section.
            name=h.group(1).strip()
            display=f'共鳴者集音：{name}（{chars[0]}）'
        else:
            # Weapon headings can be repeated/mislabeled in official cleaned text.
            display=f'武器集音：{weapons[0]}'
        p=base.PERIOD.search(segment)
        if not p: raise ValueError(f'section {i+1} missing period')
        period=segment[p.end():p.end()+180]
        if 'アップデート後' not in period[:70]: raise ValueError(f'section {i+1} unexpected start')
        end_match=base.SINGLE.search(period)
        if not end_match or not TZ.search(period[end_match.end():end_match.end()+35]):
            raise ValueError(f'section {i+1} missing explicit JST end')
        end=base.parse(end_match.group(),JST)
        if not end or not start<end: raise ValueError(f'section {i+1} invalid time range')
        entry=base.make_entry(5547,'gacha',display,start,end,'planned maintenance end and explicit JST end',planned=True)
        entries.append(entry)
    if len({e['name'] for e in entries})!=4: raise ValueError('duplicate names after featured item classification')
    return entries

def normalized(name):
    name=str(name).replace('（開始予定）','').strip()
    return name

def is_duplicate(entry,existing):
    # Legacy V14 character names are bare banner titles; compare without prefix/featured character.
    name=normalized(entry['name'])
    aliases={name}
    m=re.fullmatch(r'共鳴者集音：(.+?)（[^（）]+）',name)
    if m: aliases.add(m.group(1))
    for old in existing:
        if str(old.get('game','')).lower()!='wuwa' or str(old.get('kind','')).lower()!='gacha': continue
        if str(old.get('start',''))!=entry['start'] or str(old.get('end',''))!=entry['end']: continue
        old_name=normalized(old.get('name',''))
        if old_name in aliases or old_name==name:return True
    return any(old.get('id')==entry['id'] for old in existing)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--events',default='events.json')
    args=parser.parse_args()
    path=Path(args.events)
    existing=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(existing,list) or not all(isinstance(x,dict) for x in existing):
        raise SystemExit('ABORT: events.json must be an array of objects')
    print('WUWA V17 FEATURED ITEM GACHA IMPORT /', 'APPLY' if args.apply else 'PREVIEW')
    print('Only explicit JST end; planned maintenance end used as start.')
    try:entries=extract()
    except Exception as e:raise SystemExit('ABORT: '+str(e))
    now=dt.datetime.now(JST)
    additions=[]
    for e in entries:
        if is_duplicate(e,existing):status='EXISTS'
        elif dt.datetime.fromisoformat(e['end']+'T'+e['end_time']).replace(tzinfo=JST)<now:status='EXPIRED'
        else:status='NEW';additions.append(e)
        print(status,e['name'],e['start'],e['start_time'],'->',e['end'],e['end_time'],'JST')
    print('FOUND:',len(entries),'NEW:',len(additions),'EXISTING:',len(existing))
    if not args.apply:
        print('PREVIEW ONLY. events.json unchanged.');return
    if not additions:
        print('NO CHANGES');return
    fd,tmp=tempfile.mkstemp(prefix='.wuwa-v17-',suffix='.tmp',dir=str(path.resolve().parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(existing+additions,f,ensure_ascii=False,indent=2)
            f.write('\n')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print('APPLIED:',len(additions),'new events; existing entries preserved')

if __name__=='__main__':main()
