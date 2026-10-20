#!/usr/bin/env python3
"""V71: discover candidates for review, import only explicitly approved exact-date entries."""
import argparse, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'.reports/nte-v71/report.json'
APPROVED=ROOT/'games/nte/approved/v71.json'
REQUIRED={'id','game','name','kind','start','end','official_url','source_status'}
def valid(e):
    if not isinstance(e,dict) or not REQUIRED.issubset(e) or e.get('game')!='nte':return False
    if not all(isinstance(e[k],str) and e[k].strip() for k in REQUIRED):return False
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',e['start']) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',e['end']):return False
    from datetime import date
    try: a,b=date.fromisoformat(e['start']),date.fromisoformat(e['end'])
    except ValueError:return False
    return a<=b and e['official_url'].startswith('https://nte.perfectworld.com/') and e.get('reviewed') is True

def run(events, approved, discovery):
    if not isinstance(events,list):raise ValueError('events.json must contain a list')
    if not isinstance(approved,list):raise ValueError('approved manifest must contain a list')
    existing_ids={e.get('id') for e in events if isinstance(e,dict)}
    existing_keys={(e.get('game'),e.get('name'),e.get('start'),e.get('end')) for e in events if isinstance(e,dict)}
    add=[]; skipped=[]; rejected=[]; seen=set()
    for e in approved:
        if not valid(e):rejected.append({'id':e.get('id') if isinstance(e,dict) else None,'reason':'invalid_or_not_reviewed'});continue
        key=(e['game'],e['name'],e['start'],e['end'])
        if e['id'] in existing_ids or key in existing_keys or e['id'] in seen or key in seen:
            skipped.append(e['id']);continue
        add.append({k:v for k,v in e.items() if k!='reviewed'})
        seen.add(e['id']);seen.add(key)
    articles=discovery.get('articles',[]) if isinstance(discovery,dict) else []
    return add,{'articles_seen':len(articles),'approved_entries':len(approved),'added':[e['id'] for e in add], 'already_present':skipped,'rejected':rejected,'auto_import_policy':'reviewed manifest only; raw extracted text is never auto-imported'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--events',default=str(ROOT/'events.json'));p.add_argument('--apply',action='store_true');args=p.parse_args()
    path=Path(args.events); events=json.loads(path.read_text(encoding='utf-8-sig'))
    approved=json.loads(APPROVED.read_text(encoding='utf-8'))
    discovery_path=ROOT/'.reports/nte-v68/report.json'
    discovery=json.loads(discovery_path.read_text(encoding='utf-8')) if discovery_path.exists() else {}
    add,report=run(events,approved,discovery)
    report['applied']=args.apply
    REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.apply and add:
        path.write_text(json.dumps(events+add,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('NTE V71:',json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
