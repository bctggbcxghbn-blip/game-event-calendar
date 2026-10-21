#!/usr/bin/env python3
"""Read-only Endfield V73 candidate audit; never modifies events.json."""
import argparse,json,re,unicodedata
from pathlib import Path

HEAD=re.compile(r'(?:\d+\.\s*)?(?:特別スカウト|再現スカウト#?\d*|武庫申請|再現申請#?\d*|[一-龥ぁ-んァ-ン・「」]+イベント|「[^」]+」スタンプラリー)\s*「([^」]+)」')
# Known names are extracted only if they occur in the source text, avoiding invented events.
KNOWN=['万象一新','玉書・申請','祖泉の新流','小枝・申請','人煙の牽く天河','月映・申請','俗世の縁','万物宿魂','墨に彩あり','カーリーの花いろ絵本','危機準備','百趣演武','魂に捧ぐ新たな一幕','帰野','天河と共に','危機契約 青藍試験作戦','理性補給','記憶の痕・呪林']
def norm(s):
 return re.sub(r'[\s「」『』【】（）()・:：#＃\-ー]+','',unicodedata.normalize('NFKC',str(s))).lower()
def audit(report,events):
 items=report.get('articles',[]); texts=[t for a in items for t in a.get('candidate_text',[])]; joined='\n'.join(texts)
 endfield=[e for e in events if norm(e.get('game','')) in ('endfield','arknightsendfield')]
 output=[]
 for name in KNOWN:
  if name not in joined:continue
  matches=[e for e in endfield if norm(name) in norm(e.get('name','')) or norm(e.get('name','')) in norm(name) and len(norm(e.get('name','')))>3]
  snippets=[s for s in texts if name in s and ('開催期間' in s or '開放期間' in s)]
  output.append({'name':name,'status':'possibly_registered' if matches else 'needs_review','existing':[{'id':e.get('id'),'name':e.get('name'),'start':e.get('start'),'end':e.get('end')} for e in matches], 'evidence':sorted(snippets,key=len)[:2]})
 return {'version':74,'article_count':len(items),'raw_candidate_text_count':len(texts),'endfield_events_in_events_json':len(endfield),'unique_named_candidates':len(output),'possibly_registered':sum(x['status']=='possibly_registered' for x in output),'needs_review':sum(x['status']=='needs_review' for x in output),'candidates':output,'notes':['Name matching is approximate; check dates and timezone manually.','This audit never changes events.json.','Candidate report is a snapshot, not a live site fetch.']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidates',default='games/endfield/endfield-v73-candidates.json');p.add_argument('--events',default='events.json');p.add_argument('--output',default='.reports/endfield-v74/audit.json');a=p.parse_args()
 report=json.loads(Path(a.candidates).read_text(encoding='utf-8'));events=json.loads(Path(a.events).read_text(encoding='utf-8'))
 if isinstance(events,dict):events=events.get('events',events.get('activities',[]))
 if not isinstance(events,list):raise ValueError('Unsupported events.json structure')
 out=audit(report,events);dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Endfield V74:',out['unique_named_candidates'],'named,',out['possibly_registered'],'possible matches,',out['needs_review'],'review needed')
if __name__=='__main__':main()
