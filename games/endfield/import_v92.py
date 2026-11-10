#!/usr/bin/env python3
"""V92: idempotent Endfield official start-date markers; no invented end dates."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def apply(root=ROOT):
    path = root / 'events.json'
    candidates = json.loads((root/'games/endfield/v89_verified_candidates.json').read_text(encoding='utf-8'))['events']
    existing = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(existing,list): raise ValueError('events.json must be a list')
    ids = {e.get('id') for e in existing}
    if len(ids)!=len(existing): raise ValueError('Duplicate IDs in events.json')
    added=[]
    for c in candidates:
        if c.get('end_date') is not None: raise ValueError('V92 expects unconfirmed end dates')
        if c.get('status')!='review_required' or c.get('game')!='endfield': raise ValueError('Unreviewed candidate format')
        if c['id'] in ids: continue
        kind = '武器・装備ガチャ' if c['category']=='gacha' and '武庫' in c['title'] else ('新キャラガチャ' if c['category']=='gacha' else 'イベント')
        event={'id':c['id'],'game':'endfield','name':c['title'],'start':c['start_date'],'end':None,'kind':kind,
          'source_status':'公式開始日確認済み・終了日未定','official_url':'https://endfield.gryphline.com/ja-jp/news/'+c['source_cid'],
          'url':'https://endfield.gryphline.com/ja-jp/news/'+c['source_cid'],
          'end_note':c['end_condition'],'time_zone':'アジアサーバー時間（UTC+8）'}
        if c.get('start_time'): event['start_time']=c['start_time']; event['start_label']='アジアサーバー時間（UTC+8）'
        elif c.get('start_condition'): event['start_label']=c['start_condition']
        added.append(event);ids.add(c['id'])
    if added:
        path.write_text(json.dumps(existing+added,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Endfield V92: added={len(added)} existing={len(existing)}; unknown ends remain null')
    return len(added)
if __name__=='__main__': apply()
