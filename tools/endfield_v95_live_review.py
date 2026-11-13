#!/usr/bin/env python3
"""V95 read-only: retrieve official bulletin articles and flag new evidence for manual review."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = 'https://web-news.gryphline.com/api/bulletin'
APP = 'arknights_endfield_official'
DATE_PATTERN = re.compile(r'20\d{2}\s*[/年.\-]\s*\d{1,2}\s*[/月.\-]\s*\d{1,2}日?(?:\s*[（(]?\s*\d{1,2}:\d{2})?')

def fetch_json(url):
    req = Request(url, headers={'User-Agent':'Mozilla/5.0 (compatible; EndfieldCalendarV95/1.0)', 'Accept':'application/json'})
    with urlopen(req, timeout=18) as response:
        return json.loads(response.read(2_000_000).decode('utf-8'))

def detail_url(cid):
    return API + '/' + str(cid) + '?' + urlencode({'lang':'ja-jp','code':APP})

def extract_text(obj):
    if isinstance(obj, str):
        return re.sub(r'<[^>]*>', ' ', obj)
    if isinstance(obj, dict):
        return ' '.join(extract_text(v) for k,v in obj.items() if k not in ('image','images','cover','icon'))
    if isinstance(obj, list):
        return ' '.join(extract_text(v) for v in obj)
    return ''

def inspect(root, fetch=fetch_json):
    candidates=json.loads((root/'games/endfield/v89_verified_candidates.json').read_text(encoding='utf-8'))['events']
    calendar=json.loads((root/'events.json').read_text(encoding='utf-8'))
    known={e.get('id'):e for e in calendar if isinstance(e,dict)}
    cids=sorted({str(e['source_cid']) for e in candidates})
    articles={}
    for cid in cids:
        try:
            payload=fetch(detail_url(cid))
            data=payload.get('data',payload) if isinstance(payload,dict) else payload
            text=extract_text(data)
            articles[cid]={'status':'fetched','date_mentions':list(dict.fromkeys(DATE_PATTERN.findall(text)))[:30],
                           'text_preview':text[:1500], 'text_length':len(text)}
        except Exception as exc:
            articles[cid]={'status':'fetch_failed','error':f'{type(exc).__name__}: {exc}'}
    items=[]
    for e in candidates:
        cid=str(e['source_cid']);article=articles[cid]
        existing=known.get(e['id'])
        items.append({'id':e['id'],'title':e['title'],'source_cid':cid,'registered':existing is not None,
                      'calendar_end':existing.get('end') if existing else None,
                      'end_condition':e.get('end_condition'), 'source_status':article['status'],
                      'review_status':'already_dated' if existing and existing.get('end') else 'manual_review_required',
                      'note':'Dates mentioned in an article are NOT necessarily this event’s end date. Never auto-apply.'})
    return {'version':95,'mode':'read_only','checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'official_api':API,'articles':articles,'items':items,
            'pending':sum(x['review_status']=='manual_review_required' for x in items),
            'warning':'Live official source fetched when accessible. Dates are evidence only; no end date is inferred or changed.'}

def main():
    root=Path(__file__).resolve().parents[1]
    report=inspect(root)
    out=root/'artifacts/endfield-v95';out.mkdir(parents=True,exist_ok=True)
    (out/'official-live-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Endfield V95 official live review','',f"Pending manual review: {report['pending']} / {len(report['items'])}",'',
           'Dates found in an article are NOT verified end dates. No calendar edits are performed.','']
    for cid,a in report['articles'].items():
        lines.append(f"## Article {cid}: {a['status']}")
        lines.append('Date mentions: '+(', '.join(a.get('date_mentions',[])) or '(none / unavailable)'))
        if a.get('error'): lines.append('Error: '+a['error'])
        lines.append('')
    lines.extend(f"- {x['title']}: {x['review_status']} ({x['end_condition']})" for x in report['items'])
    (out/'official-live-review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f"ENDFIELD V95: {len(report['items'])} events; {report['pending']} pending; articles: "+', '.join(f"{k}={v['status']}" for k,v in report['articles'].items()))
    print('NO_WRITES: events.json unchanged')

if __name__=='__main__': main()
