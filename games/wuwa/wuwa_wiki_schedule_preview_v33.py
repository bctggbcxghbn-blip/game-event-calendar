#!/usr/bin/env python3
"""V33: inspect Japanese wiki version pages for gacha/event schedules (read only).

Uses only Python standard library. Dates from wiki are UNVERIFIED and never
promoted to official timestamps. No events.json writes or imports.
"""
import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import re
import urllib.request
import urllib.error

BASE = 'https://wikiwiki.jp/w-w/'
VERSION_RE = re.compile(r'^Ver\d+(?:\.\d+){1,2}$', re.I)
DATE_RE = re.compile(r'(?:20\d{2}\s*[年/.-]\s*)?\d{1,2}\s*[月/.-]\s*\d{1,2}\s*日?')
KEY_RE = re.compile(r'集音|ガチャ|ピックアップ|イベント|開催期間|スケジュール|共鳴者|武器|前半|後半|第一期|第二期')

class WikiParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.buf = []
        self.rows = []
        self.cells = []
        self.cell = None
        self.heading = None
        self.headings = []
        self.links = []
        self.link = None
        self.link_buf = []
        self.image_urls = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append(tag)
        if tag == 'tr': self.cells = []
        if tag in ('td','th'): self.cell = []
        if tag in ('h1','h2','h3','h4'): self.heading = [tag, []]
        if tag == 'a':
            self.link = a.get('href',''); self.link_buf=[]
        if tag == 'img':
            src = a.get('src') or a.get('data-src') or ''
            if src: self.image_urls.append(src)
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
        if self.heading is not None: self.heading[1].append(data)
        if self.link is not None: self.link_buf.append(data)
    def handle_endtag(self, tag):
        if tag in ('td','th') and self.cell is not None:
            self.cells.append(' '.join(''.join(self.cell).split())); self.cell=None
        if tag == 'tr' and self.cells:
            self.rows.append(self.cells[:]); self.cells=[]
        if tag in ('h1','h2','h3','h4') and self.heading is not None and tag == self.heading[0]:
            self.headings.append(' '.join(''.join(self.heading[1]).split())); self.heading=None
        if tag == 'a' and self.link is not None:
            label = ' '.join(''.join(self.link_buf).split())
            if label: self.links.append((label,self.link))
            self.link=None;self.link_buf=[]
        if self.tags:
            if tag in self.tags: self.tags=self.tags[:len(self.tags)-1-self.tags[::-1].index(tag)]

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; CalendarSchedulePreview/1.0)'})
    with urllib.request.urlopen(req,timeout=20) as r:
        raw=r.read(4_000_000)
        ct=r.headers.get_content_charset() or 'utf-8'
    return raw.decode(ct,errors='replace')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--version',default='Ver3.7',help='Wiki version, e.g. Ver3.7')
    ap.add_argument('--max-rows',type=int,default=35)
    ap.add_argument('--max-links',type=int,default=20)
    args=ap.parse_args()
    if not VERSION_RE.fullmatch(args.version): ap.error('Invalid version: expected Ver3.7 format')
    url=BASE+args.version
    print('WUWA V33 JAPANESE WIKI SCHEDULE PREVIEW / READ ONLY')
    print('SOURCE:',url)
    print('WIKI_UNVERIFIED: true; dates are not confirmed JST timestamps')
    print('NO_APPLY: events.json never modified')
    try: page=fetch(url)
    except Exception as exc:
        print('FETCH_ERROR:',type(exc).__name__,str(exc)[:220]);raise SystemExit(1)
    p=WikiParser();p.feed(page)
    print('HTML_BYTES:',len(page.encode('utf-8')),'TABLE_ROWS:',len(p.rows),'HEADINGS:',len(p.headings),'IMAGES:',len(p.image_urls))
    print('RELEVANT_HEADINGS:')
    for h in p.headings:
        if KEY_RE.search(h): print('  HEADING:',h[:180])
    candidates=[]
    for cells in p.rows:
        line=' | '.join(c for c in cells if c)
        if line and (KEY_RE.search(line) or DATE_RE.search(line)):
            candidates.append((line, bool(DATE_RE.search(line))))
    print('SCHEDULE_ROW_CANDIDATES:',len(candidates),'ROWS_WITH_DATE_TEXT:',sum(has for _,has in candidates))
    for line,has_date in candidates[:max(0,args.max_rows)]:
        print(('DATE_TEXT ' if has_date else 'RELATED   ')+line[:450])
    if len(candidates)>args.max_rows:print('TRUNCATED_ROWS:',len(candidates)-args.max_rows)
    related=[(name,url) for name,url in p.links if KEY_RE.search(name) or re.search(r'Ver\d+\.\d+',name)]
    print('RELATED_LINKS:',len(related))
    for name,href in related[:max(0,args.max_links)]: print('LINK:',name[:90], '|',href[:220])
    print('SUMMARY: WIKI_ROWS=',len(candidates),'DATE_ROWS=',sum(has for _,has in candidates),'READ_ONLY=true')
    print('NEXT: compare wiki date ranges to official article dates; do not infer hours from wiki date-only entries.')

if __name__=='__main__': main()
