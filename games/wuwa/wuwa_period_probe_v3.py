#!/usr/bin/env python3
"""Read-only diagnostic: inspect official Wuwa periods, including version-relative dates."""
import datetime as dt
import html
import json
import re
import urllib.request
from zoneinfo import ZoneInfo

ROOT = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/jp'
JST = ZoneInfo('Asia/Tokyo')
DATE = r'20\d{2}\s*(?:年|[-/])\s*\d{1,2}\s*(?:月|[-/])\s*\d{1,2}\s*日?\s*\d{1,2}\s*[:：時]\s*\d{2}'
PAIR = re.compile(r'('+DATE+r')\s*(?:~|～|〜|－|–|—|から)\s*('+DATE+r')')
ONE = re.compile(DATE)

def get(path):
    req = urllib.request.Request(ROOT+path, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=25) as f: return json.load(f)

def clean(s):
    s=html.unescape(re.sub(r'<[^>]+>',' ',str(s or '')))
    return re.sub(r'\s+',' ',s).strip()

def iso(s, utc8=False):
    v=re.findall(r'\d+',s)
    if len(v)<5: return None
    zone=dt.timezone(dt.timedelta(hours=8)) if utc8 else JST
    try: return dt.datetime(*map(int,v[:5]),tzinfo=zone).astimezone(JST)
    except ValueError: return None

def main():
    print('WUWA PERIOD PROBE V3 / READ ONLY / events.json unchanged')
    rows=get('/MainMenu.json').get('article',[])
    now=dt.datetime.now(JST)
    recent=[]
    for r in rows:
        title=clean(r.get('articleTitle'))
        if not any(x in title for x in ('メンテナンスのお知らせ','共鳴者・武器集音','イベント予告','イベント詳細','開催のお知らせ','逆境深塔','深塔','無音区','戦歌復唱')): continue
        try: pub=dt.datetime.fromisoformat(r['startTime']).replace(tzinfo=JST)
        except (KeyError,ValueError): continue
        if pub < now-dt.timedelta(days=90): continue
        recent.append((r,title))
    print('RECENT CANDIDATES:',len(recent))
    version_ends={}
    for r,title in recent:
        if 'メンテナンスのお知らせ' not in title: continue
        aid=r['articleId']; body=clean(get('/article/'+str(aid)+'.json').get('articleContent',''))
        version=re.search(r'Ver\.?\s*(\d+\.\d+)',title,re.I)
        marker=re.search(r'メンテナンス日時.{0,110}',body)
        pairs=list(PAIR.finditer(body))
        print('\nMAINTENANCE',aid,title)
        print(' LABEL:',marker.group(0) if marker else 'NOT FOUND')
        print(' PAIRS:',len(pairs))
        if pairs:
            m=pairs[0]; start,end=iso(m.group(1),True),iso(m.group(2),True)
            print(' UTC+8 -> JST:',start,end)
            if version and start and end: version_ends[version.group(1)]=end
    print('\nVERSION PLANNED STARTS:',{k:str(v) for k,v in version_ends.items()})
    for r,title in recent:
        if '集音' not in title and 'イベント予告' not in title and 'イベント詳細' not in title: continue
        aid=r['articleId']; body=clean(get('/article/'+str(aid)+'.json').get('articleContent',''))
        pairs=list(PAIR.finditer(body)); dates=ONE.findall(body)
        version=re.search(r'Ver\.?\s*(\d+\.\d+)',title,re.I)
        rel='アップデート後' in body or 'アップデート終了後' in body
        print('\nARTICLE',aid,title[:85]); print(' FULL_RANGES:',len(pairs),'DATES:',len(dates),'AFTER_UPDATE:',rel)
        for m in pairs[:3]: print(' RANGE:',m.group(1),'->',m.group(2))
        if not pairs: print(' DATES:',dates[:5])
        if rel and version: print(' VERSION START REFERENCE:',version_ends.get(version.group(1),'NOT FOUND'))
    print('\nDONE. Preview only; no files modified.')

if __name__=='__main__': main()
