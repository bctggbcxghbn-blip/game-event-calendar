#!/usr/bin/env python3
"""V68: discover official NTE update articles and extract review candidates safely."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from nte_discover_v60 import INDEX, discover
from nte_article_preview_v61 import extract

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / '.reports/nte-v68/report.json'

def fetch(url):
    if urlparse(url).hostname != 'nte.perfectworld.com' or not url.startswith('https://'):
        raise ValueError('Untrusted article host')
    req = Request(url, headers={'User-Agent':'Mozilla/5.0 (NTE calendar event discovery)'})
    with urlopen(req, timeout=15) as response:
        return response.read(3_000_000).decode('utf-8', errors='replace')

def analyze(index_html, fetch_article, max_articles=5):
    articles = discover(index_html)[:max_articles]
    result = {'status':'ok', 'source':INDEX, 'articles':[], 'auto_imported':0,
              'note':'Candidates are not automatically imported: nearby dates are not verified event periods.'}
    for item in articles:
        try:
            report = extract(fetch_article(item['url']), item['url'])
            result['articles'].append({'title':item['title'], 'version':item['version'],
                'url':item['url'], 'status':'review_required',
                'candidate_count':report['candidate_count'], 'candidates':report['candidates']})
        except Exception as exc:
            result['articles'].append({'url':item['url'], 'status':'fetch_error', 'error':str(exc)})
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--index-html-file',type=Path)
    p.add_argument('--report',type=Path,default=REPORT)
    p.add_argument('--max-articles',type=int,default=5)
    p.add_argument('--strict',action='store_true')
    args=p.parse_args()
    try:
        if not 1 <= args.max_articles <= 10: raise ValueError('max-articles must be 1..10')
        index_html=args.index_html_file.read_text(encoding='utf-8') if args.index_html_file else fetch(INDEX)
        result=analyze(index_html,fetch,args.max_articles)
    except Exception as exc:
        result={'status':'fetch_error','error':str(exc),'articles':[],'auto_imported':0}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('NTE V68',result['status'],'articles=',len(result['articles']),'auto_imported=0')
    if args.strict and result['status']!='ok': raise SystemExit(1)
if __name__=='__main__':main()
