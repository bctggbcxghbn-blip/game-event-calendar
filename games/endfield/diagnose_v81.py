#!/usr/bin/env python3
"""V81: read-only diagnostics for official Endfield bulletin API hints."""
import json
import re
import urllib.request
import urllib.error
from pathlib import Path

JS_URL = 'https://web-static.hg-cdn.com/endfield/official-v4/_next/static/chunks/226-391dfae38d9c8c93.js'
BASE = 'https://endfield.gryphline.com'
OUT = Path('.reports/endfield-v81/report.json')
MAX_BYTES = 2_000_000

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'GameEventCalendar-Diagnostics/1.0', 'Accept': 'application/json,text/plain,*/*'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return {'url':url,'status':r.status,'error':'response too large'}
            return {'url':url,'status':r.status,'final_url':r.url,'content_type':r.headers.get('Content-Type',''),'text':data.decode('utf-8','replace')}
    except urllib.error.HTTPError as e:
        return {'url':url,'status':e.code,'error':str(e)}
    except Exception as e:
        return {'url':url,'error':type(e).__name__+': '+str(e)[:250]}

def contexts(js, term='/api/bulletin', radius=450):
    return [{'offset':m.start(), 'snippet':js[max(0,m.start()-radius):m.end()+radius]} for m in list(re.finditer(re.escape(term),js))[:8]]

def summarize_api(result):
    out = {k:v for k,v in result.items() if k!='text'}
    raw = result.get('text','')
    out['bytes_text'] = len(raw)
    try:
        obj = json.loads(raw)
        out['json_type'] = type(obj).__name__
        if isinstance(obj,dict):
            out['json_keys'] = list(obj)[:25]
            # No arbitrary content copied: metadata only
            for k,v in list(obj.items())[:15]:
                if isinstance(v,list):out.setdefault('list_lengths',{})[k]=len(v)
    except (ValueError,TypeError):
        out['preview'] = re.sub(r'<[^>]+>',' ',raw[:220]).strip()[:180]
    return out

def main():
    js=fetch(JS_URL)
    report={'version':81,'mode':'read_only_api_diagnostics','javascript':{k:v for k,v in js.items() if k!='text'},'contexts':contexts(js.get('text','')),'api_checks':[],'warning':'API path is unverified; HTTP 200 does not prove it returns article listings.'}
    # Probe only two public GET endpoints, no guessing tokens, POST or pagination.
    for url in (BASE+'/api/bulletin', BASE+'/api/bulletin/'):
        report['api_checks'].append(summarize_api(fetch(url)))
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Wrote',OUT,'JS contexts:',len(report['contexts']))
    for item in report['api_checks']: print(item['url'],item.get('status'),item.get('content_type'),item.get('json_keys'))

if __name__=='__main__':main()
