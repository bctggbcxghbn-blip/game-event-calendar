#!/usr/bin/env python3
"""V35 Wuwa Wiki schedule extraction + conservative duplicate audit. READ ONLY.
Requires Python standard library only. Does not modify events.json.
"""
import argparse, datetime as dt, html, json, re, sys, urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE='https://wikiwiki.jp/w-w/'
DATE=re.compile(r'20\d{2}/\d{1,2}/\d{1,2}')
VERSION=re.compile(r'Ver\d+(?:\.\d+)?')
WEAPON_TYPES=('増幅器','手甲','長刃','迅刀','拳銃')

def norm(s):
    return re.sub(r'[\s\u3000「」『』（）()・:：—－\-]', '',str(s or '')).casefold()

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.rows=[];self.row=None;self.cell=None;self.link=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        elif tag in ('td','th') and self.row is not None:self.cell={'parts':[],'links':[]}
        elif tag=='a' and self.cell is not None:self.link=[]
        elif tag=='br' and self.cell is not None:self.cell['parts'].append('\n')
    def handle_data(self,data):
        if self.cell is not None:self.cell['parts'].append(data)
        if self.link is not None:self.link.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.link is not None:
            val=''.join(self.link).strip()
            if val:self.cell['links'].append(val)
            self.link=None
        elif tag in ('td','th') and self.cell is not None:
            self.cell['text']=''.join(self.cell['parts']);self.row.append(self.cell);self.cell=None
        elif tag=='tr' and self.row is not None:
            if self.row:self.rows.append(self.row)
            self.row=None

def split_names(cell,kind):
    text=cell['text'];links=list(dict.fromkeys(cell['links']))
    if kind=='character':
        # Each character is usually an anchor; fallback is manual review, not speculative split.
        return links, bool(text.strip() and not links)
    # Weapon text is "type・name"; preserve unlinked weapon names as well.
    parts=re.split(r'(?=(?:増幅器|手甲|長刃|迅刀|拳銃)\s*[・･])',text)
    names=[]
    for part in parts:
        m=re.match(r'\s*(?:増幅器|手甲|長刃|迅刀|拳銃)\s*[・･]\s*(.+)',part,re.S)
        if m:
            value=re.sub(r'\s+',' ',m.group(1)).strip(' ・･\n')
            if value:names.append(value)
    if not names:names=links
    # Avoid concatenating adjacent weapon names if page formatting changes.
    return list(dict.fromkeys(names)), bool(text.strip() and not names)

def get_rows(raw,version):
    parser=TableParser();parser.feed(raw);out=[];holds=[]
    for row in parser.rows:
        if len(row)<6:continue
        phase=''.join(row[0]['text'].split())
        if not re.fullmatch(r'\d+(?:\.\d+)?[前後]',phase) or not phase.startswith(version[3:]):continue
        dates=DATE.findall(row[1]['text'])
        if len(dates)!=2:holds.append((phase,'BAD_DATE'));continue
        start,end=[dt.datetime.strptime(d,'%Y/%m/%d').date().isoformat() for d in dates]
        if start>end:holds.append((phase,'REVERSED_DATES'));continue
        for kind,index in (('character',3),('weapon',5)):
            names,problem=split_names(row[index],kind)
            if problem:holds.append((phase,kind+' UNPARSED_CELL '+row[index]['text'][:80].strip()))
            for name in names:
                if name:out.append(dict(phase=phase,kind=kind,name=name,start=start,end=end))
    return out,holds

def load_events(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    events=data if isinstance(data,list) else data.get('events',[])
    if not isinstance(events,list):raise ValueError('events is not a list')
    return events

def existing_match(rec,events):
    result=[]; target=norm(rec['name'])
    for event in events:
        if not isinstance(event,dict) or event.get('game')!='wuwa':continue
        fields=[event.get(k,'') for k in ('name','original_name','banner_name','pickup','title')]
        exact=any(target==norm(f) for f in fields if f)
        # Only treat substring as a possible duplicate, not a confirmed one.
        contains=any(len(target)>=2 and target in norm(f) for f in fields if f)
        if exact or contains:result.append(event.get('id','unknown'))
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--version',default='Ver3.7');ap.add_argument('--events',default='events.json')
    ap.add_argument('--html-file',help='Use saved HTML for offline tests')
    args=ap.parse_args()
    if not VERSION.fullmatch(args.version):ap.error('version must look like Ver3.7')
    print('WUWA V35 WIKI GACHA EXTRACTION / READ ONLY')
    print('NO_APPLY=true DATE_ONLY=true No events.json writes')
    try:
        if args.html_file:raw=Path(args.html_file).read_text(encoding='utf-8')
        else:
            req=urllib.request.Request(BASE+args.version,headers={'User-Agent':'Mozilla/5.0 WuwaCalendar/1.0'})
            with urllib.request.urlopen(req,timeout=20) as r:raw=r.read().decode('utf-8','replace')
        events=load_events(args.events)
    except Exception as exc:
        print('FETCH_OR_READ_ERROR',repr(exc));return 1
    records,holds=get_rows(raw,args.version)
    print('WIKI_RECORDS:',len(records),'EXISTING_EVENTS:',len(events))
    for h in holds:print('HOLD',*h)
    today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    seen=set();counts={'CANDIDATE':0,'EXPIRED':0,'DUPLICATE':0}
    for r in records:
        key=(r['phase'],r['kind'],norm(r['name']),r['start'],r['end'])
        if key in seen:continue
        seen.add(key)
        matches=existing_match(r,events)
        if matches:status='DUPLICATE';print('HOLD POSSIBLE_DUPLICATE',r['phase'],r['kind'].upper(),r['name'],'IDS='+','.join(matches[:5]))
        elif r['end']<today:status='EXPIRED';print('HOLD EXPIRED',r['phase'],r['kind'].upper(),r['name'])
        else:status='CANDIDATE';print('REVIEW_CANDIDATE WIKI_DATE_ONLY',r['phase'],r['kind'].upper(),r['name'],r['start'],'->',r['end'])
        counts[status]+=1
    print('SUMMARY: UNIQUE=%d REVIEW_CANDIDATE=%d DUPLICATE_HOLD=%d EXPIRED_HOLD=%d PARSE_HOLD=%d READ_ONLY=true' % (len(seen),counts['CANDIDATE'],counts['DUPLICATE'],counts['EXPIRED'],len(holds)))
    print('NOTE: Wiki is community-maintained. Review names and duplicate aliases before import. Dates have no confirmed time zone.')
    return 0

if __name__=='__main__':sys.exit(main())
