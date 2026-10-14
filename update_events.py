#!/usr/bin/env python3
"""指定された公開JSONフィードからイベントを取り込み、events.jsonを更新する。"""
import json, urllib.request, pathlib, datetime
ROOT=pathlib.Path(__file__).resolve().parent
GAMES={'genshin','wuwa','hsr','zzz','nte','arknights','endfield'}
def valid(x):
 try:
  assert isinstance(x,dict) and x['game'] in GAMES
  assert all(isinstance(x[k],str) and x[k] for k in ('id','name','start','end','kind'))
  a=datetime.date.fromisoformat(x['start']); b=datetime.date.fromisoformat(x['end'])
  assert a<=b and len(x['id'])<200 and len(x['name'])<200
  assert x.get('url','').startswith(('https://','http://',''))
  return True
 except (KeyError,ValueError,TypeError,AssertionError): return False

def main():
 p=ROOT/'events.json'; current=json.loads(p.read_text()); merged={x['id']:x for x in current if valid(x)}
 feeds=json.loads((ROOT/'sources.json').read_text()).get('feeds',[])
 for url in feeds:
  try:
   if not url.startswith('https://'): raise ValueError('HTTPS URL only')
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'GameCalendarUpdater/1.0'}),timeout=15) as r:
    raw=r.read(2_000_001)
   if len(raw)>2_000_000: raise ValueError('feed too large')
   rows=json.loads(raw)
   if not isinstance(rows,list):raise ValueError('expected JSON array')
   for x in rows:
    if valid(x): merged[x['id']]=x
  except Exception as ex: print('Feed skipped:',url,ex)
 out=sorted(merged.values(),key=lambda x:(x['start'],x['game'],x['name']))
 p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(f'{len(out)} events saved from {len(feeds)} feeds')
if __name__=='__main__':main()
