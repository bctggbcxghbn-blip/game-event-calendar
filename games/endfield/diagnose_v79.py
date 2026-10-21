"""V79 read-only diagnostic: inspect first-party JS asset references for news API hints."""
import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = 'https://endfield.gryphline.com'
NEWS = ROOT + '/ja-jp/news'
MAX_BYTES = 1_500_000
KEYWORDS = re.compile(r'news|article|notice|api|graphql|information|list', re.I)
PATH_HINT = re.compile(r'(?:https?://[^\s"\'`<>\\]{5,180}|/[\w./?=&%-]{5,180})', re.I)

class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.scripts=[]
    def handle_starttag(self, tag, attrs):
        if tag != 'script': return
        d=dict(attrs)
        if d.get('src'): self.scripts.append(d['src'])

def first_party_assets(html, base=NEWS, limit=12):
    p=AssetParser(); p.feed(html)
    seen=[]
    for src in p.scripts:
        url=urljoin(base,src)
        if urlparse(url).hostname == urlparse(ROOT).hostname and url not in seen:
            seen.append(url)
    return seen[:limit]

def hints(text, max_hints=35):
    out=[]
    # Only include short URLs/paths with relevant words; never dump scripts or credentials.
    for m in PATH_HINT.finditer(text.replace('\\/', '/')):
        candidate=m.group(0).rstrip('.,;:')
        if KEYWORDS.search(candidate) and candidate not in out:
            out.append(candidate[:180])
        if len(out)>=max_hints: break
    return out

def fetch(url):
    req=Request(url, headers={'User-Agent':'GameEventCalendar-EndfieldDiagnostics/79', 'Accept':'text/html,application/javascript,*/*'})
    with urlopen(req, timeout=18) as resp:
        data=resp.read(MAX_BYTES+1)
        if len(data)>MAX_BYTES: raise ValueError('response exceeds size limit')
        return data.decode('utf-8','replace'), resp.status, resp.geturl()

def run(fetcher=fetch, max_assets=12):
    report={'version':79,'mode':'read_only_js_diagnostics','page':NEWS,'assets':[], 'endpoint_candidates':[], 'events_added':0, 'automatically_approved':0}
    try:
        html,status,final=fetcher(NEWS)
        report['page_status']=status; report['page_final_url']=final
    except Exception as e:
        report['page_error']=str(e)[:250]; return report
    report['inline_hints']=hints(html)
    assets=first_party_assets(html,final,max_assets)
    report['script_assets_found']=len(assets)
    all_hints=[]
    for url in assets:
        item={'url':url}
        try:
            body,status,final_url=fetcher(url)
            item.update({'status':status,'final_url':final_url,'characters':len(body)})
            item['hints']=hints(body)
            all_hints.extend(item['hints'])
        except Exception as e: item['error']=str(e)[:250]
        report['assets'].append(item)
    report['endpoint_candidates']=list(dict.fromkeys(report['inline_hints']+all_hints))[:80]
    report['warning']='Hints are not verified API endpoints. No API calls or event modifications are performed.'
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--output',default='.reports/endfield-v79/report.json'); ap.add_argument('--max-assets',type=int,default=12)
    args=ap.parse_args(); result=run(max_assets=max(1,min(args.max_assets,20)))
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('V79 scripts:',result.get('script_assets_found',0),'candidates:',len(result['endpoint_candidates']))
