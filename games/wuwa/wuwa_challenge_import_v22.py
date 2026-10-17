#!/usr/bin/env python3
"""WuWa V22: cautious wiki challenge import. Preview by default; --apply adds only.
All periods are wiki-listed calendar dates, with timezone UNVERIFIED.
"""
import argparse
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

SOURCES = [
 ('逆境深塔','https://wikiwiki.jp/w-w/%E9%80%86%E5%A2%83%E6%B7%B1%E5%A1%94','現在の実験周期'),
 ('死の歌が纏う海の廃墟','https://wikiwiki.jp/w-w/%E6%AD%BB%E3%81%AE%E6%AD%8C%E3%81%8C%E7%BA%8F%E3%81%86%E6%B5%B7%E3%81%AE%E5%BB%83%E5%A2%9F','現在の更新周期'),
 ('終焉マトリクス','https://wikiwiki.jp/w-w/%E7%B5%82%E7%84%89%E3%83%9E%E3%83%88%E3%83%AA%E3%82%AF%E3%82%B9','今期の開催期間'),
]
DATE = r'(20\d{2})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})'
RANGE = re.compile(DATE+r'\s*[~～〜－–—-]\s*'+DATE)
PATH=Path('events.json')
class Plain(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[]; self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style','noscript'): self.skip+=1
  if t in ('p','div','tr','td','li','h1','h2','h3','br'): self.parts.append(' ')
 def handle_endtag(self,t):
  if t in ('script','style','noscript') and self.skip: self.skip-=1
  if t in ('p','div','tr','td','li','h1','h2','h3'): self.parts.append(' ')
 def handle_data(self,d):
  if not self.skip:self.parts.append(d)

def extract(name,url,heading):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; CalendarImporter/1.0)'})
 with urllib.request.urlopen(req,timeout=25) as response:
  if response.status!=200: raise ValueError('HTTP '+str(response.status))
  raw=response.read(2000000).decode('utf-8','replace')
 p=Plain();p.feed(raw);body=re.sub(r'\s+',' ',html.unescape(''.join(p.parts)))
 matches=[]
 for h in re.finditer(re.escape(heading),body):
  m=RANGE.search(body,h.end(),h.end()+120)
  if not m:continue
  try:
   a=dt.datetime(*map(int,m.groups()[:5]));b=dt.datetime(*map(int,m.groups()[5:]))
  except ValueError:continue
  if a>=b:continue
  matches.append((a,b,body[m.end():m.end()+55]))
 unique={(a,b) for a,b,_ in matches}
 if len(unique)!=1: raise ValueError(f'{heading}: expected one distinct period; got {len(unique)}')
 a,b=next(iter(unique))
 # Page status indicators are diagnostic only: never infer that dates are correct or current.
 marker=any('終了しました' in tail for _,_,tail in matches)
 digest=hashlib.sha256((name+'|'+a.date().isoformat()+'|'+b.date().isoformat()).encode()).hexdigest()[:14]
 return {'id':'wuwa-challenge-'+digest,'game':'wuwa','kind':'challenge','name':name,
  'start':a.date().isoformat(),'end':b.date().isoformat(),
  'source_status':'日本語Wiki掲載（日時のタイムゾーン未確認・暫定）',
  'time_zone':'unverified (wiki)','official_url':url}, a,b,marker

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 print('WUWA V22 CHALLENGE IMPORT /', 'APPLY' if args.apply else 'PREVIEW')
 print('Wiki sources, NOT official. Dates only; timezone unverified; no start_time/end_time.')
 if not PATH.exists():raise SystemExit('ERROR: events.json not found')
 events=json.loads(PATH.read_text(encoding='utf-8-sig'))
 if not isinstance(events,list) or not all(isinstance(e,dict) for e in events):raise SystemExit('ERROR: invalid events.json')
 candidates=[]
 try:
  for name,url,heading in SOURCES:
   c,a,b,ended=extract(name,url,heading)
   print(f'SOURCE: {name} | {a:%Y-%m-%d %H:%M} -> {b:%Y-%m-%d %H:%M} | WIKI TIMEZONE UNVERIFIED')
   if ended:print('REVIEW WARNING:',name,'wiki text contains 終了しました near period')
   candidates.append(c)
 except Exception as ex:raise SystemExit('ERROR: extraction failed, no changes: '+str(ex))
 new=[]
 for c in candidates:
  same=[e for e in events if str(e.get('game','')).lower()=='wuwa' and str(e.get('name','')).strip()==c['name']]
  if any(e.get('start')==c['start'] and e.get('end')==c['end'] for e in same):
   print('EXISTS:',c['name']);continue
  if any(str(e.get('id',''))==c['id'] for e in events):
   print('HOLD ID COLLISION:',c['name']);continue
  # Periodic challenges naturally recur. Keep prior periods; block only overlapping periods.
  if any(str(e.get('start',''))<=c['end'] and str(e.get('end',''))>=c['start'] for e in same):
   print('HOLD OVERLAP:',c['name'],'manual review needed');continue
  print('NEW:',c['name'],c['start'],'->',c['end']);new.append(c)
 print(f'SUMMARY: extracted={len(candidates)} new={len(new)} existing_total={len(events)}')
 if not args.apply:print('PREVIEW ONLY. events.json unchanged.');return
 if not new:print('APPLIED: 0 new events; unchanged');return
 tmp=PATH.with_name(PATH.name+'.wuwa-v22.tmp')
 try:
  tmp.write_text(json.dumps(events+new,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(PATH)
 finally:
  if tmp.exists():tmp.unlink()
 print(f'APPLIED: {len(new)} new challenge events; existing entries preserved')
 print('WARNING: wiki periods are provisional and timezone is not verified.')
if __name__=='__main__':main()
