#!/usr/bin/env python3
"""V34 Wiki + official crosscheck preview. READ ONLY; no events.json changes.
Requires V33 and V26/V24 alongside this file. Wiki dates remain date-only.
"""
import argparse
import datetime as dt
from html.parser import HTMLParser
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wuwa_wiki_schedule_preview_v33 as wiki

DATE = re.compile(r'20\d{2}/\d{1,2}/\d{1,2}')
JST = dt.timezone(dt.timedelta(hours=9))

def norm(s):
    return re.sub(r'[\s　「」『』（）()・:：—－-]', '', str(s or '')).casefold()

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[]; self.row=None; self.cell=None; self.anchor=None; self.depth=0
    def handle_starttag(self,tag,attrs):
        if tag=='tr': self.row=[]
        elif tag in ('td','th') and self.row is not None: self.cell={'text':[],'links':[]}
        elif tag=='a' and self.cell is not None: self.anchor=[]
        elif tag=='br' and self.cell is not None: self.cell['text'].append(' ')
    def handle_data(self,data):
        if self.cell is not None: self.cell['text'].append(data)
        if self.anchor is not None: self.anchor.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.anchor is not None:
            s=''.join(self.anchor).strip()
            if s and self.cell is not None: self.cell['links'].append(s)
            self.anchor=None
        elif tag in ('td','th') and self.cell is not None:
            self.cell['text']=' '.join(''.join(self.cell['text']).split())
            self.row.append(self.cell);self.cell=None
        elif tag=='tr' and self.row is not None:
            if self.row: self.rows.append(self.row)
            self.row=None

def parse_rows(html, version):
    p=Tables();p.feed(html)
    output=[]
    for row in p.rows:
        if len(row)<6: continue
        first=row[0]['text']
        if not re.fullmatch(r'\d+(?:\.\d+)?(?:前|後)', first): continue
        if not first.startswith(version.replace('Ver','')): continue
        dates=DATE.findall(row[1]['text'])
        if len(dates)!=2: continue
        start,end=[dt.datetime.strptime(x,'%Y/%m/%d').date().isoformat() for x in dates]
        if start>end: continue
        for kind,col in [('character',3),('weapon',5)]:
            cell=row[col] if col<len(row) else {'text':'','links':[]}
            names=list(dict.fromkeys(cell['links']))
            # Wiki text may contain non-linked weapon names; preserve raw text for review.
            for name in names:
                if not name or name.startswith('★'):continue
                output.append({'phase':first,'kind':kind,'name':name,'start':start,'end':end,
                               'source':'wiki_date_only','wiki_url':wiki.BASE+version})
            if not names and cell['text']:
                print('HOLD UNLINKED_CELL',first,kind,cell['text'][:120])
            elif kind=='weapon' and len(names)<2 and cell['text']:
                print('REVIEW WEAPON_CELL',first,cell['text'][:150])
    return output

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--version',default='Ver3.7')
    ap.add_argument('--events',default='events.json')
    args=ap.parse_args()
    if not wiki.VERSION_RE.fullmatch(args.version):ap.error('Use --version Ver3.7')
    print('WUWA V34 WIKI + OFFICIAL MERGE PREVIEW / READ ONLY')
    print('NO_APPLY: never modifies events.json; wiki dates are NOT confirmed JST timestamps')
    try: html=wiki.fetch(wiki.BASE+args.version)
    except Exception as e:
        print('FETCH_ERROR',repr(e));return 1
    records=parse_rows(html,args.version)
    path=Path(args.events)
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        existing=data if isinstance(data,list) else data.get('events',[])
        if not isinstance(existing,list):raise ValueError('events is not a list')
    except Exception as e:
        print('EVENTS_READ_ERROR',repr(e));return 1
    print('WIKI_RECORDS:',len(records),'EXISTING_EVENTS:',len(existing))
    # Only confirmed official timestamp ranges may be displayed as corroboration;
    # never infer hours from date-only wiki schedule or planned maintenance.
    official=[]
    try:
        import wuwa_dynamic_gacha_preview_v26 as v26
        import wuwa_official_discovery_v24 as v24
        # V34 deliberately does not invoke unstable private APIs from older scripts.
        print('OFFICIAL_MODULES: available; prior V29/V30 logs remain the authority for explicit timestamps')
    except ImportError:
        print('OFFICIAL_MODULES: unavailable; wiki-only review')
    candidates=0;duplicates=0;expired=0
    today=dt.datetime.now(JST).date().isoformat()
    seen=set()
    for rec in records:
        key=(rec['kind'],norm(rec['name']),rec['start'],rec['end'])
        if key in seen:continue
        seen.add(key)
        matches=[]
        for e in existing:
            if not isinstance(e,dict) or e.get('game')!='wuwa':continue
            enames=[e.get('name',''),e.get('original_name','')]
            if any(norm(rec['name'])==norm(n) for n in enames if n):matches.append(e.get('id','unknown'))
        if matches:
            duplicates+=1;status='HOLD POSSIBLE_DUPLICATE'
        elif rec['end']<today:
            expired+=1;status='HOLD EXPIRED'
        else:
            candidates+=1;status='REVIEW_CANDIDATE WIKI_DATE_ONLY'
        print(status,rec['phase'],rec['kind'].upper(),rec['name'],rec['start'],'->',rec['end'],
              'MATCHES='+str(len(matches)))
    print('SUMMARY: WIKI_RECORDS=%d UNIQUE=%d REVIEW_CANDIDATE=%d DUPLICATE_HOLD=%d EXPIRED_HOLD=%d READ_ONLY=true' %
          (len(records),len(seen),candidates,duplicates,expired))
    print('NOTE: linked names may omit plain-text weapons; inspect REVIEW WEAPON_CELL. No automatic imports.')
    return 0

if __name__=='__main__':raise SystemExit(main())
