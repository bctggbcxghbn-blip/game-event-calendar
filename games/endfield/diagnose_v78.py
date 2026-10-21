"""V78 read-only diagnostics for Endfield official news discovery."""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import monitor_v77 as v77

URLS = v77.SEEDS
MAX_BYTES = 2_000_000

def retrieve(url, opener=urlopen):
    request = Request(url, headers={'User-Agent':'GameEventCalendar-EndfieldDiagnostics/78 (read-only)','Accept':'text/html,application/xml,text/xml,*/*'})
    try:
        with opener(request, timeout=15) as response:
            payload = response.read(MAX_BYTES)
            return {'url':url, 'http_status':getattr(response,'status',200),
                    'final_url':response.geturl(), 'content_type':response.headers.get('Content-Type',''),
                    'bytes_read':len(payload),'body':payload.decode('utf-8','replace'),'error':None}
    except HTTPError as exc:
        return {'url':url,'http_status':exc.code,'final_url':url,'content_type':'','bytes_read':0,'body':'','error':str(exc)}
    except (URLError,TimeoutError,OSError) as exc:
        return {'url':url,'http_status':None,'final_url':url,'content_type':'','bytes_read':0,'body':'','error':str(exc)}

def summarize(page):
    body=page.get('body','')
    normalized=body.replace('\\/','/').replace('\\u002F','/').replace('\\u002f','/')
    article_urls=v77.discover({page['url']:normalized},limit=80)
    # The V77 discovery function always inserts the known baseline URL.
    discovered=[u for u in article_urls if u != v77.v76.BASE_ARTICLE]
    _,links=v77.v76.parse_page(body)
    unique_links=list(dict.fromkeys(urljoin(page['final_url'],link) for link in links))
    return {k:page.get(k) for k in ('url','http_status','final_url','content_type','bytes_read','error')} | {
        'html_anchor_count':len(links), 'unique_anchor_count':len(unique_links),
        'anchor_samples':unique_links[:25], 'new_article_urls':discovered[:40],
        'new_article_count':len(discovered),
        'dynamic_page_hint':bool(re.search(r'__NEXT_DATA__|<div[^>]+id=["\'](?:root|app)["\']|/_next/static/|<script[^>]+src=',body,re.I)),
    }

def run(retriever=retrieve):
    pages=[retriever(url) for url in URLS]
    diagnostics=[summarize(page) for page in pages]
    raw={p['url']:p.get('body','') for p in pages if p.get('http_status') == 200}
    urls=v77.discover(raw,limit=80)
    return {'version':78,'mode':'read_only_diagnostics','sources':diagnostics,
            'articles_discovered':len(urls),'article_urls':urls,
            'discovery_warning':len(urls)<=1,
            'warnings':(['Only the known article was discovered; inspect source HTTP statuses and anchor samples.'] if len(urls)<=1 else []),
            'events_json_changed':False,'automatically_approved':0,'events_added':0,
            'note':'This report diagnoses discovery only. Article dates are not approved event end dates.'}

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',default='.reports/endfield-v78/report.json')
    args=ap.parse_args()
    report=run()
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('V78: discovered',report['articles_discovered'],'articles; source statuses:',[s['http_status'] for s in report['sources']])
    if report['discovery_warning']: print('WARNING: only the known article found; check diagnostic artifact')
