"""V56 read-only calendar update audit. Run after all import/cleanup steps."""
import argparse
import collections
import datetime as dt
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / '.reports' / 'calendar-v56'

def date_only(value):
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return dt.date.fromisoformat(value[:10]) if value[:10].count('-') == 2 else None
    except ValueError:
        return None

def audit(events, previous=None, today=None):
    if not isinstance(events, list):
        return {'status':'error','critical':[{'type':'invalid_root','detail':'events.json must be an array'}]}
    today = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    critical=[]; warnings=[]
    seen=collections.defaultdict(list); signatures=collections.defaultdict(list)
    for i,e in enumerate(events):
        if not isinstance(e,dict):
            critical.append({'type':'invalid_event','index':i});continue
        eid=e.get('id');game=e.get('game');name=e.get('name')
        if not isinstance(eid,str) or not eid.strip():
            critical.append({'type':'missing_id','index':i})
        else: seen[eid].append(i)
        if not isinstance(game,str) or not game.strip() or not isinstance(name,str) or not name.strip():
            critical.append({'type':'missing_game_or_name','index':i,'id':eid})
        start=date_only(e.get('start'));end=date_only(e.get('end'))
        if start is None or end is None or start>end:
            critical.append({'type':'invalid_dates','index':i,'id':eid,'start':e.get('start'),'end':e.get('end')})
        if start and end and game and name:
            signatures[(game,name.strip(),start.isoformat(),end.isoformat(),str(e.get('kind','')))].append(eid)
    for eid,idx in seen.items():
        if len(idx)>1: critical.append({'type':'duplicate_id','id':eid,'indexes':idx})
    for key,ids in signatures.items():
        if len(ids)>1: warnings.append({'type':'possible_duplicate','game':key[0],'name':key[1],'start':key[2],'end':key[3],'kind':key[4],'ids':ids})
    prev = previous if isinstance(previous,list) else None
    before={e['id']:e for e in prev if isinstance(e,dict) and isinstance(e.get('id'),str)} if prev is not None else {}
    after={e['id']:e for e in events if isinstance(e,dict) and isinstance(e.get('id'),str)}
    added=sorted(set(after)-set(before)) if prev is not None else []
    removed=sorted(set(before)-set(after)) if prev is not None else []
    modified=sorted(k for k in set(before)&set(after) if before[k]!=after[k]) if prev is not None else []
    active=sum(bool(date_only(e.get('start')) and date_only(e.get('end')) and date_only(e.get('start'))<=today<=date_only(e.get('end'))) for e in events if isinstance(e,dict))
    return {'status':'error' if critical else ('review' if warnings else 'ok'),'date_jst':today.isoformat(),'count':len(events),'active_today':active,'counts_by_game':dict(sorted(collections.Counter(e.get('game','unknown') for e in events if isinstance(e,dict)).items())),'change_comparison_available':prev is not None,'changes':{'added':len(added),'removed':len(removed),'modified':len(modified),'added_ids':added,'removed_ids':removed,'modified_ids':modified},'critical':critical,'warnings':warnings}

def load_previous():
    try:
        result=subprocess.run(['git','show','HEAD:events.json'],cwd=ROOT,capture_output=True,text=True,timeout=8)
        if result.returncode==0:
            data=json.loads(result.stdout)
            if isinstance(data,list):return data
    except (OSError,ValueError,subprocess.TimeoutExpired):pass
    return None

def main():
    p=argparse.ArgumentParser();p.add_argument('--strict',action='store_true',help='fail on critical errors only');a=p.parse_args()
    try: events=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
    except (OSError,ValueError) as ex:
        events=None;load_error=str(ex)
    if events is None:
        result={'status':'error','critical':[{'type':'unreadable_events','detail':load_error}]}
    else: result=audit(events,load_previous())
    REPORT_DIR.mkdir(parents=True,exist_ok=True)
    path=REPORT_DIR/'report.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('V56 CALENDAR UPDATE AUDIT (READ_ONLY)')
    print('STATUS:',result['status'],'TOTAL:',result.get('count','n/a'),'ACTIVE:',result.get('active_today','n/a'))
    if result.get('change_comparison_available'):
        print('CHANGES:',result['changes']['added'],'added,',result['changes']['removed'],'removed,',result['changes']['modified'],'modified')
    else: print('CHANGES: baseline unavailable (git HEAD:events.json)')
    print('CRITICAL:',len(result['critical']),'WARNINGS:',len(result.get('warnings',[])))
    for issue in result['critical'][:15]: print('ERROR:',json.dumps(issue,ensure_ascii=False))
    for issue in result.get('warnings',[])[:15]: print('REVIEW:',json.dumps(issue,ensure_ascii=False))
    print('REPORT:',path.relative_to(ROOT))
    if a.strict and result['critical']:raise SystemExit(1)

if __name__=='__main__':main()
