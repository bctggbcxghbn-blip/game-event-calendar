"""Read-only official Endfield notice monitor; never infers or approves end dates."""
import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = 'https://endfield.gryphline.com'
INDEX = ROOT + '/ja-jp/news'
BASE_ARTICLE = INDEX + '/9560'
HERE = Path(__file__).resolve().parent
DATE_RE = re.compile(r'20\d{2}\s*[/年.-]\s*\d{1,2}\s*[/月.-]\s*\d{1,2}(?:日)?(?:\s*\d{1,2}:\d{2})?')

class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.links=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag in ('script','style'): self.skip+=1
        if tag=='a' and attrs.get('href'): self.links.append(attrs['href'])
        if tag in ('p','div','li','h1','h2','h3','br'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style') and self.skip: self.skip-=1
        if tag in ('p','div','li','h1','h2','h3'): self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)

def parse_page(source):
    parser=Extractor(); parser.feed(source)
    text=html.unescape(''.join(parser.parts))
    lines=[re.sub(r'\s+', ' ', line).strip() for line in text.splitlines()]
    return [line for line in lines if line], parser.links

def fetch(url):
    req=Request(url,headers={'User-Agent':'GameEventCalendar-EndfieldMonitor/76 (read-only)'})
    with urlopen(req,timeout=15) as response:
        return response.read(2_000_000).decode('utf-8','replace')

def notice_urls(links, limit=20):
    found=[BASE_ARTICLE]
    for link in links:
        match=re.fullmatch(r'(?:https?://endfield\.gryphline\.com)?(/ja-jp/news/\d+)(?:[?#].*)?',link)
        if match:
            url=ROOT+match.group(1)
            if url not in found: found.append(url)
        if len(found)>=limit: break
    return found

def scan(pending, pages):
    result=[]
    for event in pending:
        name=event['name']; terms=[name]
        for term in re.findall(r'「([^」]+)」',name):
            if len(term)>=3: terms.append(term)
        evidence=[]
        for url,lines in pages.items():
            for i,line in enumerate(lines):
                if not any(term in line for term in terms): continue
                context=' '.join(lines[max(0,i-2):min(len(lines),i+5)])[:1200]
                dates=DATE_RE.findall(context)
                evidence.append({'url':url,'excerpt':context,'date_mentions':dates})
                if len(evidence)>=12: break
            if len(evidence)>=12: break
        result.append({'id':event['id'],'name':name,'end_condition':event['end_condition'],
                       'status':'manual_review' if evidence else 'no_matching_notice',
                       'verified_end':None,'evidence':evidence})
    return result

def run(fetcher=fetch,pending_path=None,limit=20):
    pending=json.loads(Path(pending_path or HERE/'pending_v75.json').read_text(encoding='utf-8'))
    errors=[]; pages={}
    try:
        index_html=fetcher(INDEX)
        _,links=parse_page(index_html)
        urls=notice_urls(links,limit=limit)
    except Exception as exc:
        errors.append({'url':INDEX,'error':str(exc)}); urls=[BASE_ARTICLE]
    for url in urls:
        try: pages[url]=parse_page(fetcher(url))[0]
        except Exception as exc: errors.append({'url':url,'error':str(exc)})
    results=scan(pending,pages)
    return {'version':76,'mode':'read_only','articles_checked':len(pages),
            'articles_attempted':len(urls),'pending_count':len(pending),
            'manual_review_count':sum(r['status']=='manual_review' for r in results),
            'automatically_approved':0,'events_added':0,'results':results,'fetch_errors':errors,
            'note':'Date mentions are only evidence, NOT verified end dates. Check official event-specific notice manually.'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pending',default=str(HERE/'pending_v75.json'))
    ap.add_argument('--limit',type=int,default=20);ap.add_argument('--output',default='.reports/endfield-v76/report.json')
    args=ap.parse_args(); report=run(pending_path=args.pending,limit=max(1,min(50,args.limit)))
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Endfield V76:',report['articles_checked'],'articles,',report['manual_review_count'],'review candidates, 0 auto-approved')
    if report['fetch_errors']: print('Fetch warnings:',len(report['fetch_errors']))
