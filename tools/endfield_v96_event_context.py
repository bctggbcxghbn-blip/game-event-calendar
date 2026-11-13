#!/usr/bin/env python3
"""V96 read-only: associate official article date mentions with event-title context."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from endfield_v95_live_review import fetch_json, detail_url, extract_text, DATE_PATTERN

SPACE = re.compile(r'\s+')

def normalize(s):
    return SPACE.sub('', str(s)).replace('「','').replace('」','').replace('『','').replace('』','').replace('・','').replace(' ','')

def aliases(title):
    # Prefer distinctive full names; never match generic labels such as "イベント".
    parts = re.findall(r'「([^」]+)」', title)
    return list(dict.fromkeys([p for p in parts if len(normalize(p)) >= 4] + [title]))

def context_matches(text, title, window=240):
    compact=normalize(text)
    hits=[]
    for alias in aliases(title):
        needle=normalize(alias)
        if len(needle)<4: continue
        start=0
        while (pos:=compact.find(needle,start)) >= 0:
            lo=max(0,pos-window); hi=min(len(compact),pos+len(needle)+window)
            snippet=compact[lo:hi]
            dates=list(dict.fromkeys(DATE_PATTERN.findall(snippet)))
            hits.append({'alias':alias,'date_mentions_near_title':dates[:12], 'context':snippet[:520]})
            start=pos+len(needle)
            if len(hits)>=8:break
        if hits:break
    return hits

def inspect(root,fetch=fetch_json):
    candidates=json.loads((root/'games/endfield/v89_verified_candidates.json').read_text(encoding='utf-8'))['events']
    calendar=json.loads((root/'events.json').read_text(encoding='utf-8'))
    existing={e.get('id'):e for e in calendar if isinstance(e,dict)}
    articles={}
    for cid in sorted({str(e['source_cid']) for e in candidates}):
        try:
            payload=fetch(detail_url(cid))
            data=payload.get('data',payload) if isinstance(payload,dict) else payload
            articles[cid]={'status':'fetched','text':extract_text(data)}
        except Exception as exc:
            articles[cid]={'status':'fetch_failed','error':f'{type(exc).__name__}: {exc}','text':''}
    items=[]
    for event in candidates:
        cid=str(event['source_cid']); article=articles[cid]
        matches=context_matches(article['text'],event['title']) if article['status']=='fetched' else []
        end=existing.get(event['id'],{}).get('end')
        items.append({'id':event['id'],'title':event['title'],'source_cid':cid,'registered':event['id'] in existing,
            'calendar_end':end,'end_condition':event.get('end_condition'),
            'source_status':article['status'],'matches':matches,
            'review_status':'already_dated' if end else 'manual_review_required',
            'warning':'Nearby dates are NOT verified event end dates; may describe start, shop, or maintenance.'})
    return {'version':96,'mode':'read_only','checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'articles':{k:{kk:vv for kk,vv in a.items() if kk!='text'} for k,a in articles.items()},'items':items,
        'pending':sum(x['review_status']=='manual_review_required' for x in items),
        'warning':'No end dates inferred or changed. Verify event-specific official wording before applying.'}

def main():
    root=Path(__file__).resolve().parents[1]
    report=inspect(root)
    out=root/'artifacts/endfield-v96';out.mkdir(parents=True,exist_ok=True)
    (out/'event-date-context.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Endfield V96 event/date context review','',f"Pending: {report['pending']} / {len(report['items'])}",'',
           'Dates near an event name are NOT automatically confirmed end dates. events.json is unchanged.','']
    for item in report['items']:
        lines += [f"## {item['title']}",f"Source CID: {item['source_cid']}; status: {item['source_status']}",
                  f"End condition: {item['end_condition']}",f"Title matches: {len(item['matches'])}"]
        for hit in item['matches']:
            lines += ['Nearby dates: '+(', '.join(hit['date_mentions_near_title']) or '(none)'),
                      'Context: '+hit['context']]
        lines.append('')
    (out/'event-date-context.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f"ENDFIELD V96: {len(report['items'])} events; {report['pending']} pending; read-only")
    print('NO_WRITES: events.json unchanged')

if __name__=='__main__':main()
