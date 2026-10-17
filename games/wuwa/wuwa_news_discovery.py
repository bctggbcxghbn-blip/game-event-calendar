#!/usr/bin/env python3
"""Read-only discovery of Wuthering Waves official news and 4 categories."""
import html
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

URLS = [
    'https://wutheringwaves.kurogames.com/jp/main/news',
    'https://wutheringwaves.kurogames.com/m/jp/main/news',
    'https://wutheringwaves.kurogames.com/en/main/news',
    'https://wutheringwaves.kurogames.com/m/en/main/news',
]
CATEGORIES = {
    'EVENT': r'イベント|期間限定|報酬|Event|Limited.Time|Double Drop',
    'GACHA': r'集音|共鳴者|武器|Convene|Resonator|Weapon|Boosted Drop',
    'MAINTENANCE': r'メンテナンス|アップデート|Maintenance|Update',
    'CHALLENGE': r'逆境深塔|深層空想秘境|ホロタクティクス|Tower of Adversity|Whimpering Wastes|Illusive Realm|Challenge|Crisis Trial',
}
class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.scripts=[]; self.text=[]; self._script=False
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if tag=='a' and d.get('href'): self.links.append((d['href'], ''))
        if tag=='script':
            if d.get('src'): self.scripts.append(d['src'])
            self._script=True
    def handle_endtag(self, tag):
        if tag=='script': self._script=False
    def handle_data(self, data):
        if not self._script and data.strip(): self.text.append(data.strip())

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; calendar-news-probe/1.0)','Accept-Language':'ja,en;q=0.8'})
    with urllib.request.urlopen(req,timeout=20) as response:
        raw=response.read(2_000_000)
        charset=response.headers.get_content_charset() or 'utf-8'
        return response.status,response.geturl(),raw.decode(charset,errors='replace')

def main():
    print('WUWA OFFICIAL NEWS DISCOVERY / READ ONLY')
    print('events.json will NOT be changed.')
    for url in URLS:
        print('\n'+'='*65+'\nURL:',url)
        try: status,final,body=fetch(url)
        except Exception as exc:
            print('FETCH ERROR:',type(exc).__name__,str(exc)[:250]); continue
        parser=PageParser(); parser.feed(body)
        visible=' '.join(parser.text)
        print('HTTP:',status,'FINAL:',final,'HTML_CHARS:',len(body),'VISIBLE_CHARS:',len(visible))
        print('VISIBLE SAMPLE:',visible[:350])
        print('ARTICLE LINKS:')
        links=list(dict.fromkeys(urljoin(final,href) for href,_ in parser.links if '/news/detail/' in href or '/announcement/' in href))
        for link in links[:12]: print(' ',link)
        print('ARTICLE_LINK_COUNT:',len(links))
        print('SCRIPT SOURCES:')
        for src in parser.scripts[:12]: print(' ',urljoin(final,src))
        print('SCRIPT_COUNT:',len(parser.scripts))
        for category,pattern in CATEGORIES.items():
            matches=[]
            for m in re.finditer(pattern,visible,re.I):
                context=visible[max(0,m.start()-65):min(len(visible),m.end()+100)]
                if context not in matches: matches.append(context)
                if len(matches)>=4: break
            print(category+':',len(matches),'SAMPLES')
            for sample in matches: print('  ',sample[:190])
        api_hints=list(dict.fromkeys(re.findall(r'https?[^\s"\'<>\\]{8,160}(?:api|news|article)[^\s"\'<>\\]{0,100}',body,re.I)))
        print('API/NEWS URL HINTS:',len(api_hints))
        for hint in api_hints[:8]: print(' ',html.unescape(hint[:200]))
    print('\nDONE. If HTML is only a shell, next step is inspecting the site JavaScript/network API.')

if __name__=='__main__': main()
