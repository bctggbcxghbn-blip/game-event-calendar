#!/usr/bin/env python3
"""Import dated Arknights events from the Japanese Wiki table."""
import argparse, json, re
from datetime import date
from html.parser import HTMLParser
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

def extract(html):
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
    return list({x['id']:x for x in out}.values())

def merge(existing,incoming):
    ids={x['id'] for x in incoming}; keys={(x.get('game'),x.get('name'),x.get('start'),x.get('end')) for x in incoming}; out=[x for x in existing if x.get('id') not in ids and (x.get('game'),x.get('name'),x.get('start'),x.get('end')) not in keys]; out.extend(incoming); return sorted(out,key=lambda x:(x.get('start',''),x.get('game',''),x.get('id','')))

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--path',type=Path,default=ROOT/'events.json');p.add_argument('--html-file',type=Path);a=p.parse_args(); html=a.html_file.read_text(encoding='utf-8') if a.html_file else urlopen(Request(SOURCE,headers={'User-Agent':'GameEventCalendar/1.0'}),timeout=15).read().decode('utf-8','replace'); data=json.loads(a.path.read_text(encoding='utf-8')); incoming=[x for x in extract(html) if x['end'] >= date.today().isoformat()]; out=merge(data,incoming); print(f'Arknights Wiki: dated_events={len(incoming)} total={len(data)}->{len(out)}');
    if a.apply and out!=data:a.path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
