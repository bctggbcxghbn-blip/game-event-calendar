#!/usr/bin/env python3
"""V62: compare V61 text candidates with V59 canonical NTE entries (read-only)."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from nte_official_v59 import official_events

# Distinctive source terms, curated against the supplied V61 report.
TERMS={
 'kurobane':['新限定Sランクキャラ「クロバネ」'],
 'requiem':['限定Sランクキャラ「レクイエム」復刻'],
 'sin-punishment':['新限定Sランク弧盤「罪と罰」'],
 'last-rose':['限定Sランク弧盤「ラスト・ローズ」復刻'],
 'seven-days':['ログインボーナス「7Daysボーナス」'],
 'puka-festival':['期間限定イベント「プカ遊園祭」'],
 'extreme-rank':['期間限定イベント「極限昇段戦」'],
 'treasure':['期間限定イベント「炭団子の秘宝」'],
 'stamina':['期間限定イベント「スタミナブースト」'],
 'pixel':['期間限定イベント「ピクセルオーバーフロー」'],
 'porsche-new':['ブラインドボックス「ファントムラン」'],
 'porsche-return':['ブラインドボックス「エバードライブ」復刻'],
 'invitation':['Webイベント「クロバネの招待状」'],
 'costume':['「蒼羽ソワレ」'],
}
# A V61 candidate is not a source paragraph with guaranteed start/end dates.
def compare(report):
 if report.get('status')!='ok' or not isinstance(report.get('candidates'),list):
  raise ValueError('Expected successful V61 report with candidates list')
 candidates=report['candidates']
 existing=official_events()
 matched_indices=set()
 rows=[]
 for event in existing:
  slug=event['id'].removeprefix('nte-official-v14-')
  terms=TERMS[slug]
  indices=[i for i,c in enumerate(candidates) if any(t in c.get('source_text','') for t in terms)]
  matched_indices.update(indices)
  rows.append({'id':event['id'],'name':event['name'],'kind':event['kind'],
               'existing_start':event['start'],'existing_end':event['end'],
               'source_candidate_indices':indices,'status':'matched_heading' if indices else 'needs_review',
               'period_verified':False})
 return {'status':'ok','source_candidate_count':len(candidates),
         'registered_v59_count':len(rows),'matched_registered':sum(r['status']=='matched_heading' for r in rows),
         'unmatched_registered':sum(r['status']=='needs_review' for r in rows),
         'non_heading_or_unmatched_candidate_count':len(candidates)-len(matched_indices),
         'registered_items':rows,'unmatched_candidates':[
             {'index':i,'source_text':c.get('source_text','')[:240]}
             for i,c in enumerate(candidates) if i not in matched_indices],
         'auto_imported':0,
         'note':'Heading matches only; dates are from V59 and NOT re-verified by V61 text evidence.'}

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--input',type=Path,default=ROOT/'tests/fixtures/nte_v61_candidates.json')
 p.add_argument('--report',type=Path,default=ROOT/'.reports/nte-v62/report.json')
 args=p.parse_args()
 result=compare(json.loads(args.input.read_text(encoding='utf-8')))
 args.report.parent.mkdir(parents=True,exist_ok=True)
 args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('NTE V62 REVIEW registered={registered_v59_count} matched={matched_registered} needs_review={unmatched_registered} leftover_text={non_heading_or_unmatched_candidate_count} auto_imported=0'.format(**result))
 print('REPORT:',args.report)
if __name__=='__main__':main()
