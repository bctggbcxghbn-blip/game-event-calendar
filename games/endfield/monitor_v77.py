"""V77: discover official Japanese news through index, sitemap and embedded URLs; read-only."""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import monitor_v76 as v76

ROOT = 'https://endfield.gryphline.com'
SEEDS = [ROOT + '/ja-jp/news', ROOT + '/sitemap.xml', ROOT + '/robots.txt']
ARTICLE = re.compile(r'(?:https?://endfield\.gryphline\.com)?/ja-jp/news/(\d{3,12})(?!\d)')

def discover(raw_pages, limit=40):
    found = [v76.BASE_ARTICLE]
    for body in raw_pages.values():
        # Handles anchor href, sitemap loc, JSON-escaped slashes and raw embedded paths.
        body = body.replace('\\/', '/').replace('\\u002F', '/').replace('\\u002f', '/')
        for match in ARTICLE.finditer(body):
            url = ROOT + '/ja-jp/news/' + match.group(1)
            if url not in found:
                found.append(url)
            if len(found) >= limit:
                return found
    return found

def run(fetcher=v76.fetch, pending_path=None, limit=40):
    pending = json.loads(Path(pending_path or HERE/'pending_v75.json').read_text(encoding='utf-8'))
    errors=[]; raw={}; pages={}
    for url in SEEDS:
        try: raw[url]=fetcher(url)
        except Exception as exc: errors.append({'url':url,'error':str(exc)})
    urls=discover(raw, limit=limit)
    for url in urls:
        try: pages[url]=v76.parse_page(fetcher(url))[0]
        except Exception as exc: errors.append({'url':url,'error':str(exc)})
    results=v76.scan(pending,pages)
    return {'version':77,'mode':'read_only','discovery_sources':list(raw),
        'articles_discovered':len(urls),'articles_checked':len(pages),
        'pending_count':len(pending),'manual_review_count':sum(r['status']=='manual_review' for r in results),
        'automatically_approved':0,'events_added':0,'results':results,
        'fetch_errors':errors,'article_urls':urls,
        'discovery_warning': 'If only one article is discovered, the official site may load news dynamically; this is not full monitoring.',
        'note':'Dates near event names are not verified event end dates. Manual approval required.'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pending',default=str(HERE/'pending_v75.json'))
    ap.add_argument('--limit',type=int,default=40);ap.add_argument('--output',default='.reports/endfield-v77/report.json')
    a=ap.parse_args(); report=run(pending_path=a.pending,limit=max(1,min(a.limit,80)))
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('V77:',report['articles_discovered'],'discovered,',report['articles_checked'],'checked, 0 approved')
