#!/usr/bin/env python3
"""Import dated Arknights events from the Japanese Wiki table."""
import argparse, json, re
from datetime import date
from html.parser import HTMLParser
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
SOURCE='https://arknights.wikiru.jp/'
RANGE=re.compile(r'(20\d{2})/(\d{1,2})/(\d{1,2})\s*\d{1,2}:\d{2}\s*[〜～~-]\s*(?:(20\d{2})/)?(\d{1,2})/(\d{1,2})\s*\d{1,2}:\d{2}')

class TableRows(HTMLParser):
    def __init__(self): super().__init__(); self.rows=[]; self.cells=[]; self.buf=[]; self.in_cell=False
    def handle_starttag(self,t,a):
        if t=='tr': self.cells=[]
        elif t in ('td','th'): self.buf=[]; self.in_cell=True
    def handle_data(self,d):
        if self.in_cell:self.buf.append(d)
    def handle_endtag(self,t):
        if t in ('td','th') and self.in_cell:self.cells.append(' '.join(''.join(self.buf).split()));self.in_cell=False
        elif t=='tr' and self.cells:self.rows.append(self.cells)

class Paragraphs(HTMLParser):
    def __init__(self): super().__init__(); self.items=[]; self.buf=[]; self.in_p=False
    def handle_starttag(self,t,a):
        if t=='p': self.buf=[]; self.in_p=True
    def handle_data(self,d):
        if self.in_p: self.buf.append(d)
    def handle_endtag(self,t):
        if t=='p' and self.in_p:
            self.items.append(' '.join(''.join(self.buf).split())); self.in_p=False

HEADING = re.compile(r'<h([1-6])\b[^>]*>(.*?)</h\1>', re.I | re.S)
JP_HEADINGS = ('開催中のイベント', '開催予定のイベント')
CN_MARKERS = ('大陸版', '中国版', '実装順', '周回予定表')

def _heading_text(value):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', unescape(value))).strip()

def jp_sections(html):
    matches=list(HEADING.finditer(html)); chunks=[]; active=False; level=None; found=False
    for i,m in enumerate(matches):
        title=_heading_text(m.group(2)); n=int(m.group(1)); end=matches[i+1].start() if i+1<len(matches) else len(html)
        if any(marker in title for marker in CN_MARKERS): active=False; level=None
        elif any(label in title for label in JP_HEADINGS): active=True; level=n; found=True
        elif active and level is not None and n<=level: active=False; level=None
        if active: chunks.append(html[m.end():end])
    if found and chunks and RANGE.search(''.join(chunks)):
        return ''.join(chunks)
    # Current Wiki also renders the event lists as labelled paragraphs rather
    # than heading elements. Keep this fallback bounded by the next 終了 block.
    starts=[html.find(label) for label in JP_HEADINGS if html.find(label)>=0]
    if starts:
        start=min(starts); start=html.rfind('<p', 0, start); end=html.find('<p><strong>終了', start)
        return html[start:] if end<0 else html[start:end]
    return ''

def extract(html, require_jp_section=False):
    if require_jp_section:
        html=jp_sections(html)
        if not html: return []
    p=TableRows();p.feed(html); out=[]
    for row in p.rows:
        text=' '.join(row); m=RANGE.search(text)
        if not m or not row: continue
        name=row[0].strip()
        if not name or name in {'イベント名','期間限定イベント'}: continue
        sy,sm,sd=m.group(1),m.group(2),m.group(3); ey=m.group(4) or sy; em,ed=m.group(5),m.group(6)
        start=f'{sy}-{int(sm):02d}-{int(sd):02d}'; end=f'{ey}-{int(em):02d}-{int(ed):02d}'
        try: date.fromisoformat(start);date.fromisoformat(end)
        except ValueError: continue
        kind='ガチャ' if 'スカウト' in name else 'イベント'; slug=re.sub(r'[^0-9A-Za-z一-龯ぁ-んァ-ヶ]+','-',name).strip('-')[:60]
        out.append({'id':f'arknights-wiki-{slug}-{start}','game':'arknights','name':name,'kind':kind,'start':start,'end':end,'official_url':SOURCE,'source_status':'アークナイツ日本語Wiki'})
    q=Paragraphs(); q.feed(html)
    for text in q.items:
        m=RANGE.search(text)
        if not m: continue
        name=text[:m.start()].strip().rstrip('(').strip()
        if name.startswith('開催予定のイベント'):
            name=name[len('開催予定のイベント'):].strip()
        if not name or name in {'イベント名','期間限定イベント'}: continue
        sy,sm,sd=m.group(1),m.group(2),m.group(3); ey=m.group(4) or sy; em,ed=m.group(5),m.group(6)
        start=f'{sy}-{int(sm):02d}-{int(sd):02d}'; end=f'{ey}-{int(em):02d}-{int(ed):02d}'
        try: date.fromisoformat(start);date.fromisoformat(end)
        except ValueError: continue
        kind='ガチャ' if 'スカウト' in name else 'イベント'; slug=re.sub(r'[^0-9A-Za-z一-龯ぁ-んァ-ヶ]+','-',name).strip('-')[:60]
        out.append({'id':f'arknights-wiki-{slug}-{start}','game':'arknights','name':name,'kind':kind,'start':start,'end':end,'official_url':SOURCE,'source_status':'アークナイツ日本語Wiki'})
    return list({x['id']:x for x in out}.values())

def merge(existing,incoming):
    ids={x['id'] for x in incoming}; keys={(x.get('game'),x.get('name'),x.get('start'),x.get('end')) for x in incoming}; out=[x for x in existing if x.get('id') not in ids and (x.get('game'),x.get('name'),x.get('start'),x.get('end')) not in keys]; out.extend(incoming); return sorted(out,key=lambda x:(x.get('start',''),x.get('game',''),x.get('id','')))

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--path',type=Path,default=ROOT/'events.json');p.add_argument('--html-file',type=Path);a=p.parse_args(); html=a.html_file.read_text(encoding='utf-8') if a.html_file else urlopen(Request(SOURCE,headers={'User-Agent':'GameEventCalendar/1.0'}),timeout=15).read().decode('utf-8','replace'); data=json.loads(a.path.read_text(encoding='utf-8')); scoped=jp_sections(html); incoming=[x for x in extract(scoped) if x['end'] >= date.today().isoformat()] if scoped else []; print('Arknights Wiki: JP sections not found; no automatic registration' if not scoped else f'Arknights Wiki: JP sections found; dated_events={len(incoming)}'); out=merge(data,incoming); print(f'total={len(data)}->{len(out)}');
    if a.apply and out!=data:a.path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
