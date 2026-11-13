#!/usr/bin/env python3
"""V93: read-only audit of Endfield candidates and their unconfirmed end dates."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def audit(root=ROOT):
    candidates=json.loads((root/'games/endfield/v89_verified_candidates.json').read_text(encoding='utf-8'))['events']
    events=json.loads((root/'events.json').read_text(encoding='utf-8'))
    by_id={e.get('id'):e for e in events if e.get('game')=='endfield'}
    rows=[]
    for c in candidates:
        e=by_id.get(c['id'])
        actual_end=e.get('end') if e else None
        rows.append({'id':c['id'],'title':c['title'],'start':c['start_date'],
          'registered':bool(e),'calendar_end':actual_end,'candidate_end':c.get('end_date'),
          'end_condition':c.get('end_condition'), 'source_cid':c.get('source_cid'),
          'review_status': 'not_registered' if not e else ('date_present_needs_source_review' if actual_end else 'end_unconfirmed')})
    return {'version':93,'mode':'read_only','total':len(rows),'registered':sum(r['registered'] for r in rows),
            'unconfirmed':sum(r['review_status']=='end_unconfirmed' for r in rows), 'items':rows,
            'note':'Calendar dates are not independently verified against new official notices. No automatic changes.'}

def main():
    result=audit()
    out=ROOT/'.reports/endfield-v93';out.mkdir(parents=True,exist_ok=True)
    (out/'end-date-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Endfield V93 終了日監査','',f"登録済み: {result['registered']}/{result['total']} / 終了日未確定: {result['unconfirmed']}",'','| イベント | カレンダー終了日 | 状態 |','|---|---|---|']
    for r in result['items']: lines.append(f"| {r['title']} | {r['calendar_end'] or '未定'} | {r['review_status']} |")
    lines+=['','※ 新しい公式発表の確認は別途必要。終了日を推測して登録しません。']
    (out/'end-date-audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f"ENDFIELD_V93 registered={result['registered']}/{result['total']} unconfirmed={result['unconfirmed']} report={out}")
if __name__=='__main__':main()
