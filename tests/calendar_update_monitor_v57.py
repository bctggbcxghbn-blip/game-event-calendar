"""V57 update monitoring: conservative read-only warnings, no external requests."""
import argparse
import collections
import datetime as dt
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.reports' / 'calendar-v57' / 'report.json'
GAMES = ('genshin','wuwa','hsr','zzz','nte','arknights','endfield')

def as_date(value):
    try:
        if isinstance(value,str) and len(value)>=10:
            return dt.date.fromisoformat(value[:10])
    except ValueError:
        pass
    return None

def assess(current, previous=None, today=None, last_change_days=None):
    today = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    warnings=[]; critical=[]
    if not isinstance(current,list):
        return {'status':'error','critical':[{'code':'INVALID_CURRENT_DATA'}],'warnings':[]}
    curr=collections.Counter(x.get('game') for x in current if isinstance(x,dict))
    prev=collections.Counter(x.get('game') for x in previous if isinstance(x,dict)) if isinstance(previous,list) else None
    if prev is not None:
        if len(previous)>=20 and len(current)<len(previous)*0.7:
            warnings.append({'code':'LARGE_TOTAL_DROP','before':len(previous),'after':len(current)})
        for game,count in prev.items():
            if count>=5 and curr[game]<count*0.5:
                warnings.append({'code':'LARGE_GAME_DROP','game':game,'before':count,'after':curr[game]})
        if previous==current and last_change_days is not None and last_change_days>=7:
            warnings.append({'code':'NO_DATA_CHANGE_7_DAYS','days':last_change_days,'note':'May be normal; check upstream sources'})
    # No upcoming events can be normal for an unreleased game: report only for games already present.
    for game,count in curr.items():
        if count<3:continue
        ends=[as_date(e.get('end')) for e in current if isinstance(e,dict) and e.get('game')==game]
        ends=[d for d in ends if d]
        if ends and max(ends)<today:
            warnings.append({'code':'NO_CURRENT_OR_FUTURE_EVENTS','game':game,'latest_end':max(ends).isoformat()})
    return {'status':'review' if warnings else 'ok','date_jst':today.isoformat(),
            'total':len(current),'previous_total':len(previous) if isinstance(previous,list) else None,
            'counts_by_game':dict(sorted((str(k),v) for k,v in curr.items())),
            'last_change_days':last_change_days,'warnings':warnings,'critical':critical,
            'baseline_available':prev is not None}

def git_previous():
    try:
        p=subprocess.run(['git','show','HEAD:events.json'],cwd=ROOT,text=True,capture_output=True,timeout=10)
        if p.returncode==0:
            data=json.loads(p.stdout)
            if isinstance(data,list):return data
    except (OSError,ValueError,subprocess.TimeoutExpired):pass
    return None

def git_age(today):
    # Shallow history may omit the latest data change: absence is unknown, not stale.
    try:
        p=subprocess.run(['git','log','-1','--format=%cI','--','events.json'],cwd=ROOT,text=True,capture_output=True,timeout=10)
        if p.returncode==0 and p.stdout.strip():
            changed=dt.datetime.fromisoformat(p.stdout.strip()).date()
            return max(0,(today-changed).days)
    except (OSError,ValueError,subprocess.TimeoutExpired):pass
    return None

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--strict',action='store_true',help='Fail only for unreadable input, not monitoring warnings')
    args=parser.parse_args()
    today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    try:
        current=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
        report=assess(current,git_previous(),today,git_age(today))
    except (OSError,ValueError) as exc:
        report={'status':'error','warnings':[],'critical':[{'code':'UNREADABLE_EVENTS','detail':str(exc)}]}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('V57 CALENDAR UPDATE MONITOR (READ_ONLY)')
    print('STATUS:',report['status'],'TOTAL:',report.get('total','n/a'),'BASELINE:',report.get('baseline_available',False))
    print('WARNINGS:',len(report.get('warnings',[])),'CRITICAL:',len(report.get('critical',[])))
    for issue in report.get('warnings',[]):print('WARNING:',json.dumps(issue,ensure_ascii=False))
    for issue in report.get('critical',[]):print('ERROR:',json.dumps(issue,ensure_ascii=False))
    print('REPORT:',OUT.relative_to(ROOT))
    if args.strict and report['critical']:raise SystemExit(1)

if __name__=='__main__':main()
