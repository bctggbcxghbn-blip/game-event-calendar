#!/usr/bin/env python3
"""Read-only diagnostics for webpack module 56006, Endfield official website."""
import json,re,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urljoin,urlparse
PAGE='https://endfield.gryphline.com/ja-jp/news'
CDN='web-static.hg-cdn.com'
OUT=Path('.reports/endfield-v83/report.json')
MAX_JS=45
MAX_BYTES=3_000_000

def fetch(url):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'GameEventCalendar-Diagnostics/1.0'})
        with urllib.request.urlopen(req,timeout=15) as r:
            raw=r.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:return {'status':r.status,'error':'size limit'}
            return {'status':r.status,'text':raw.decode('utf-8','replace')}
    except urllib.error.HTTPError as e:return {'status':e.code,'error':str(e)}
    except Exception as e:return {'error':type(e).__name__+': '+str(e)[:120]}

def script_urls(html):
    links=re.findall(r'<script\b[^>]*\bsrc=["\']([^"\']+)',html,re.I)
    result=[]
    for link in links:
        u=urljoin(PAGE,link)
        if urlparse(u).hostname in ('endfield.gryphline.com',CDN) and urlparse(u).path.endswith('.js') and u not in result:result.append(u)
    return result

def module_contexts(js,limit=8):
    # Require a module declaration, not merely a reference such as a(56006).
    patterns=[r'(?<!\d)56006\s*:\s*(?:function\s*\(|\([^)]{1,100}\)\s*=>|[A-Za-z_$][\w$]*\s*=>)',r'(?<!\d)56006\s*:\s*\(']
    spans=[]
    for pat in patterns:
        for m in re.finditer(pat,js):
            if any(abs(m.start()-p)<20 for p in spans):continue
            spans.append(m.start())
    out=[]
    for pos in spans[:limit]:
        snippet=js[max(0,pos-100):min(len(js),pos+1800)]
        snippet=re.sub(r'(?i)((?:token|secret|password|api[_-]?key|authorization)["\']?\s*[:=]\s*["\'])[^"\']+',r'\1[REDACTED]',snippet)
        out.append({'offset':pos,'excerpt':snippet,'cms_host_literals':re.findall(r'(?:host|appCode)\s*:\s*["\']([^"\']{1,180})',snippet)[:10]})
    return out

def main():
    page=fetch(PAGE)
    urls=script_urls(page.get('text',''))
    report={'version':83,'mode':'read_only','page_status':page.get('status'),'scripts_discovered':len(urls),'scripts_inspected':0,'module_56006':[],'errors':[],'warning':'Extracted snippets are unverified. No API requests or event modifications.'}
    for url in urls[:MAX_JS]:
        res=fetch(url)
        report['scripts_inspected']+=1
        if res.get('status')!=200:
            report['errors'].append({'url':url,'status':res.get('status'),'error':res.get('error')});continue
        contexts=module_contexts(res['text'])
        if contexts:report['module_56006'].append({'url':url,'matches':contexts})
    if not report['module_56006']:report['warning']='Module definition not found in inspected initial script tags; may be loaded dynamically.'
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('V83 scanned:',report['scripts_inspected'],'module bundles:',len(report['module_56006']),'report:',OUT)

if __name__=='__main__':main()
