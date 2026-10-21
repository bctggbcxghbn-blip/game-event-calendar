import argparse, json
from pathlib import Path

SOURCE='https://endfield.gryphline.com/ja-jp/news/9560'
HERE=Path(__file__).resolve().parent

def run(events_path, approvals_path, apply=False):
    events=json.loads(Path(events_path).read_text(encoding='utf-8'))
    if not isinstance(events,list): raise ValueError('events.json must be an array')
    approved=json.loads(Path(approvals_path).read_text(encoding='utf-8'))
    pending=json.loads((HERE/'pending_v75.json').read_text(encoding='utf-8'))
    ids={x.get('id') for x in events}
    names={x.get('name') for x in events if x.get('game')=='endfield'}
    added=[]; waiting=[]; existing=[]
    for x in pending:
        if x['id'] in ids or x['name'] in names:
            existing.append(x['name']);continue
        end=approved.get(x['id'])
        if not isinstance(end,dict) or not end.get('end'):
            waiting.append(x['name']);continue
        if not isinstance(end['end'],str) or len(end['end'])!=10:
            raise ValueError('end must be YYYY-MM-DD: '+x['id'])
        from datetime import date
        date.fromisoformat(end['end'])
        if date.fromisoformat(end['end'])<date.fromisoformat(x['start']):
            raise ValueError('end before start: '+x['id'])
        item={k:v for k,v in x.items() if k not in ('end_condition','review_status')}
        item.update(end=end['end'],source_status='公式開始日確認済み・終了日は承認ファイルで確認',end_note=x['end_condition'])
        if end.get('end_time'): item['end_time']=end['end_time']
        events.append(item);added.append(x['name'])
        ids.add(x['id']);names.add(x['name'])
    report={'version':75,'existing':existing,'waiting_for_verified_end':waiting,'ready_to_add':added,'applied':bool(apply)}
    if apply and added: Path(events_path).write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--events',default='events.json');p.add_argument('--approvals',default=str(HERE/'approved_ends_v75.json'));p.add_argument('--apply',action='store_true');a=p.parse_args()
    report=run(a.events,a.approvals,a.apply)
    out=Path('.reports/endfield-v75/report.json');out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
