#!/usr/bin/env python3
"""V82 read-only Endfield JS configuration diagnostics. No API calls or event edits."""
import json
import re
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urljoin, urlparse

PAGE='https://endfield.gryphline.com/ja-jp/news'
CDN='web-static.hg-cdn.com'
OUT=Path('.reports/endfield-v82/report.json')
MAX_JS=12
MAX_BYTES=2_000_000
TERMS=('appCode','baseURL','baseUrl','api/bulletin','cms:', 'tabs:', 'bulletin','axios.create')

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'GameEventCalendar-Diagnostics/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:
            data=response.read(MAX_BYTES+1)
            if len(data)>MAX_BYTES: return {'url':url,'status':response.status,'error':'response too large'}
            return {'url':url,'status':response.status,'text':data.decode('utf-8','replace')}
    except urllib.error.HTTPError as e: return {'url':url,'status':e.code,'error':str(e)}
    except Exception as e: return {'url':url,'error':type(e).__name__+': '+str(e)[:180]}

def scripts(html):
    urls=re.findall(r'<script\b[^>]*\bsrc=["\']([^"\']+)',html,re.I)
    result=[]
    for url in urls:
        full=urljoin(PAGE,url)
        host=urlparse(full).hostname or ''
        if host in ('endfield.gryphline.com',CDN) and full.endswith('.js') and full not in result:
            result.append(full)
    return result

def contexts(js,radius=170,limit=15):
    found=[]
    for term in TERMS:
        for match in list(re.finditer(re.escape(term),js,re.I))[:4]:
            excerpt=js[max(0,match.start()-radius):min(len(js),match.end()+radius)]
            # Do not leak query tokens or any bearer-style secrets in the report.
            excerpt=re.sub(r'(?i)(authorization|token|secret|password|api[_-]?key)(["\']?\s*[:=]\s*["\'])[^"\']+',r'\1\2[REDACTED]',excerpt)
            found.append({'term':term,'offset':match.start(),'snippet':excerpt})
            if len(found)>=limit:return found
    return found

def main():
    page=fetch(PAGE)
    found=scripts(page.get('text',''))
    # Known API client bundle is added even if page no longer exposes it.
    known='https://web-static.hg-cdn.com/endfield/official-v4/_next/static/chunks/226-391dfae38d9c8c93.js'
    if known not in found:found.insert(0,known)
    # Favor bundles likely to contain API configuration.
    found=sorted(found,key=lambda x:(0 if '226-391df' in x else 1,0 if '/chunks/' in x else 1,x))
    report={'version':82,'mode':'read_only_js_config_diagnostics','page':{'url':PAGE,'status':page.get('status'),'error':page.get('error')},'script_count':len(found),'scripts':[],'warning':'Candidates are unverified; no API request or event update is made.'}
    for url in found[:MAX_JS]:
        result=fetch(url)
        js=result.get('text','')
        report['scripts'].append({'url':url,'status':result.get('status'),'error':result.get('error'),'bytes':len(js.encode('utf-8')),'matches':contexts(js)})
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('V82 scripts discovered:',len(found),'inspected:',len(report['scripts']),'matches:',sum(len(x['matches']) for x in report['scripts']))
    print('Saved',OUT)

if __name__=='__main__':main()
