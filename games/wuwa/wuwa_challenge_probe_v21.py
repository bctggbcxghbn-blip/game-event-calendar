#!/usr/bin/env python3
"""WuWa V21 periodic challenge source diagnostic. Read only; standard library only."""
import html
import re
import urllib.request
from html.parser import HTMLParser

SOURCES = [
    ('逆境深塔', 'https://wikiwiki.jp/w-w/%E9%80%86%E5%A2%83%E6%B7%B1%E5%A1%94'),
    ('死の歌が纏う海の廃墟', 'https://wikiwiki.jp/w-w/%E6%AD%BB%E3%81%AE%E6%AD%8C%E3%81%8C%E7%BA%8F%E3%81%86%E6%B5%B7%E3%81%AE%E5%BB%83%E5%A2%9F'),
    ('終焉マトリクス', 'https://wikiwiki.jp/w-w/%E7%B5%82%E7%84%89%E3%83%9E%E3%83%88%E3%83%AA%E3%82%AF%E3%82%B9'),
    ('更新情報・実装予定', 'https://wikiwiki.jp/w-w/%E6%9B%B4%E6%96%B0%E6%83%85%E5%A0%B1'),
]
class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript'): self.skip+=1
        if tag in ('p','div','tr','td','li','h1','h2','h3','br'): self.parts.append(' ')
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript') and self.skip:self.skip-=1
        if tag in ('p','div','tr','td','li','h1','h2','h3'): self.parts.append(' ')
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def main():
    print('WUWA V21 PERIODIC CHALLENGE SOURCES / READ ONLY')
    print('NO apply mode. No changes to events.json. Wiki sources are NOT official.')
    for name,url in SOURCES:
        print('\nSOURCE:',name,'URL:',url)
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; CalendarSourceAudit/1.0)'})
            with urllib.request.urlopen(req,timeout=18) as response:
                raw=response.read(1800000).decode('utf-8','replace')
            parser=Text();parser.feed(raw)
            body=re.sub(r'\s+',' ',html.unescape(''.join(parser.parts)))
            print('FETCH: OK; TEXT_CHARS:',len(body))
            terms=('現在の実験周期','現在の開催期間','現在の周期','開催期間','更新周期','2026/10/12','2026/11/09','4週間','終焉マトリクス','死の歌が纏う海の廃墟')
            shown=0
            for term in terms:
                for m in list(re.finditer(re.escape(term),body,re.I))[:2]:
                    excerpt=body[max(0,m.start()-90):min(len(body),m.end()+220)]
                    print('CONTEXT',term+':',excerpt[:350]);shown+=1
                    if shown>=12:break
                if shown>=12:break
            patterns=[r'20\d{2}\s*[/年.-]\s*\d{1,2}\s*[/月.-]\s*\d{1,2}\s*日?\s*\d{1,2}:\d{2}\s*[~～〜－–—-]\s*20\d{2}\s*[/年.-]\s*\d{1,2}\s*[/月.-]\s*\d{1,2}\s*日?\s*\d{1,2}:\d{2}',r'20\d{2}/\d{1,2}/\d{1,2}\s*\d{1,2}:\d{2}']
            matches=[]
            for pattern in patterns:matches.extend(re.findall(pattern,body))
            print('DATE_MATCHES:',list(dict.fromkeys(matches))[:15])
            if not matches:print('REVIEW: no precise dated range found; do not generate a calendar entry.')
        except Exception as e:
            print('FETCH ERROR:',type(e).__name__,str(e)[:220])
    print('\nDONE. Diagnostic only; do not assume unverified timezone or predict dates.')
if __name__=='__main__':main()
