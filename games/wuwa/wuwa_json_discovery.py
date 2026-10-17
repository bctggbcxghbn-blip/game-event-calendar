#!/usr/bin/env python3
"""Read-only Wuthering Waves official article JSON discovery."""
import re
import urllib.request
from urllib.parse import urljoin

BASE = 'https://wutheringwaves.kurogames.com'
JS = BASE + '/static4.0/assets/index-40f080d8.js'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; WuwaCalendarProbe/1.0)'}

def fetch(url, limit=6_000_000):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=18) as resp:
        data = resp.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Response too large')
        return resp.status, data.decode('utf-8', 'replace')

def show_context(js, needle, limit=3):
    matches = list(re.finditer(re.escape(needle), js, re.I))
    print(f'{needle}: {len(matches)} matches')
    for match in matches[-limit:]:
        snippet = js[max(0, match.start()-380): match.end()+480]
        snippet = re.sub(r'(?i)(CLIENT_SECRET|api_secret|authorization|token)(["\s:=]+)[^,}\s]+', r'\1\2[REDACTED]', snippet)
        print('  CONTEXT:', snippet[:900].replace('\n', ' '))

print('WUWA OFFICIAL JSON DISCOVERY / READ ONLY')
print('events.json will NOT be changed.')
try:
    status, js = fetch(JS)
    print('JS HTTP:', status, 'CHARS:', len(js))
except Exception as exc:
    print('JS FETCH ERROR:', type(exc).__name__, str(exc)[:220])
    raise SystemExit(0)

for term in ['getArticleMenuJson', 'getArticleJson', 'ArticleMenu.json', 'Article.json', 'VITE_APP_JSON_PATH', 'akiwebsite/website2.0/json']:
    show_context(js, term)

print('\nJSON ROOT CANDIDATES:')
roots = re.findall(r'VITE_APP_JSON_PATH(?:_[A-Z]+)?:\s*["\'](https?://[^"\']+)', js)
roots += re.findall(r'https?://[^"\'\s,]+/akiwebsite/website2\.0/json/[^"\'\s,}]+', js)
roots = list(dict.fromkeys(x.rstrip('\\') for x in roots))
for root in roots[:12]:
    print('ROOT:', root)

# Only request directly referenced article-menu file at a discovered official JSON root.
for root in roots[:6]:
    url = urljoin(root.rstrip('/') + '/', 'ArticleMenu.json')
    print('\nTRY:', url)
    try:
        status, body = fetch(url, 1_500_000)
        print('HTTP:', status, 'CHARS:', len(body))
        print('SAMPLE:', body[:900].replace('\n', ' '))
    except Exception as exc:
        print('ERROR:', type(exc).__name__, str(exc)[:180])
print('\nDONE. Share the output for the next step.')
