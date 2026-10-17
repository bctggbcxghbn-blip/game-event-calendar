#!/usr/bin/env python3
"""WuWa V18: look for independent official JST/UTC+8 timing for server-time events. Read-only."""
import json,re,urllib.request,html,datetime as dt
BASE='https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/jp/'
TARGETS=['天工の探し物','無音イレイサー','潮騒探検・玄方地界','傍らに響く雨音のプレゼント','群響シミュレーション','ブブ企画・旅立']
TZ=re.compile(r'(日本標準時|JST|UTC\s*[+＋]\s*8|サーバー時間)')
DATE=re.compile(r'20\d{2}年\d{1,2}月\d{1,2}日\s*\d{1,2}[:：時]\d{2}')
def get(path):
 req=urllib.request.Request(BASE+path,headers={'User-Agent':'Mozilla/5.0'})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def plain(s):
 s=html.unescape(str(s or ''))
 s=re.sub(r'<[^>]+>',' ',s)
 return re.sub(r'\s+',' ',s)
def rows(x):
 if isinstance(x,list):
  for v in x:yield from rows(v)
 elif isinstance(x,dict):
  if 'articleId' in x and ('articleTitle' in x or 'articleDesc' in x):yield x
  else:
   for v in x.values():yield from rows(v)
def main():
 print('WUWA V18 OFFICIAL CROSS-ARTICLE TIMEZONE CHECK / READ ONLY',flush=True)
 print('Only an explicit timezone attached to the SAME event period is evidence.',flush=True)
 data=get('MainMenu.json')
 pool={str(r['articleId']):r for r in rows(data)}
 print('OFFICIAL ARTICLES INDEXED:',len(pool),flush=True)
 # Search recent titles/descriptions first; only fetch relevant bodies and newest news.
 ranked=[]
 for aid,r in pool.items():
  title=plain(r.get('articleTitle'))
  desc=plain(r.get('articleDesc'))
  score=100 if any(t in title or t in desc for t in TARGETS) else 0
  if any(t in title for t in ['イベント','コンテンツ紹介','お知らせ','開催']):score+=1
  if score:ranked.append((score,aid,title))
 ranked.sort(key=lambda v:(-v[0],-int(v[1]) if v[1].isdigit() else 0))
 selected=ranked[:75]
 print('ARTICLES TO CHECK:',len(selected),flush=True)
 counts={t:0 for t in TARGETS}
 evidence=0
 for _,aid,title in selected:
  try:
   item=get('article/'+aid+'.json')
   body=plain(item.get('articleContent',''))
  except Exception as ex:
   print('FETCH ERROR:',aid,str(ex)[:120],flush=True);continue
  for target in TARGETS:
   if target not in body and target not in title:continue
   counts[target]+=1
   print('\nEVENT:',target,'ARTICLE:',aid,'TITLE:',title[:110],flush=True)
   for m in list(re.finditer(re.escape(target),body))[:2]:
    snippet=body[max(0,m.start()-80):min(len(body),m.end()+700)]
    dates=DATE.findall(snippet)
    zones=TZ.findall(snippet)
    print('  CONTEXT:',snippet[:500],flush=True)
    print('  DATES:',dates[:5],'TIMEZONE TERMS:',zones[:8],flush=True)
    # Do not assert conversion based on co-occurrence in a whole article.
    if dates and any(z in ('日本標準時','JST','UTC+8') for z in zones):
     print('  REVIEW: explicit timezone appears nearby; verify it belongs to the event period.',flush=True)
     evidence+=1
 print('\nSUMMARY: mentions=',counts,'possible_contexts=',evidence,flush=True)
 print('NO timezone mapping assumed. NO file changes. NO apply mode.',flush=True)
if __name__=='__main__':main()
