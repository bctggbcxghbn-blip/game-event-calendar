#!/usr/bin/env python3
"""Read-only: inspect public Wuthering Waves site JS for news API endpoints."""
import re
import urllib.request

URL = 'https://wutheringwaves.kurogames.com/static4.0/assets/index-40f080d8.js'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/javascript,*/*'}
PATTERNS = [
    ('API BASE', r'mc-api\.kurogame\.com|/web_site'),
    ('NEWS FUNCTIONS', r'getNews|newsList|articleList|articleDetail|news/list|news/detail|article/list|article/detail|initArticleJson|initArticleMenuJson'),
    ('HTTP CALLS', r'\.get\(|\.post\(|fetch\(|baseURL|axios\.create'),
]

def clean(s):
    s = re.sub(r'(?i)(authorization|token|secret|password|api[_-]?key)(["\']?\s*[:=]\s*["\']?)[^,}\s"\']+', r'\1\2[REDACTED]', s)
    return s.replace('\n', ' ').replace('\r', ' ')

def main():
    print('WUWA API DETAIL PROBE / READ ONLY')
    print('events.json will NOT be changed.')
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=35) as response:
        js = response.read(8_000_000).decode('utf-8', errors='replace')
        print('HTTP:', response.status, 'JS_CHARS:', len(js))
    for label, pattern in PATTERNS:
        matches = list(re.finditer(pattern, js, re.I))
        print('\n===', label, 'MATCHES:', len(matches), '===')
        for m in matches[:12]:
            start, end = max(0, m.start()-260), min(len(js), m.end()+360)
            print('OFFSET:', m.start(), 'CONTEXT:', clean(js[start:end])[:700])
    paths = sorted(set(re.findall(r'["\'`](/(?:web_site|api|news|article)[^"\'`\s]{1,160})["\'`]', js, re.I)))
    print('\n=== POSSIBLE API PATHS:', len(paths), '===')
    for p in paths[:50]: print(clean(p))
    print('\nDONE. Paste this log to continue.')

if __name__ == '__main__':
    main()
