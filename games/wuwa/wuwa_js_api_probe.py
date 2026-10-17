#!/usr/bin/env python3
"""Read-only probe for Wuthering Waves official website JavaScript API hints."""
import re
import urllib.request
from urllib.parse import urljoin

BASE = 'https://wutheringwaves.kurogames.com'
PAGES = [BASE + '/jp/main/news', BASE + '/en/main/news']
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; WuwaNewsProbe/1.0)', 'Accept': '*/*'}
KEYWORDS = re.compile(r'news|article|notice|announcement|api|list|content|activity|banner|gacha|maintenance|challenge|post', re.I)

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read().decode('utf-8', errors='replace')

def main():
    print('WUWA JAVASCRIPT API DISCOVERY - READ ONLY')
    print('events.json will NOT be changed.')
    scripts = set()
    for page in PAGES:
        print('\nPAGE:', page)
        try:
            html = fetch(page)
            found = re.findall(r'<script\b[^>]*\bsrc=["\']([^"\']+)', html, re.I)
            print('SCRIPTS:', len(found))
            for src in found:
                url = urljoin(page, src)
                print(' ', url)
                if 'index-' in url or 'assets/' in url:
                    scripts.add(url)
        except Exception as exc:
            print('ERROR:', type(exc).__name__, str(exc)[:200])
    for script in sorted(scripts):
        if 'polyfills' in script:
            continue
        print('\n' + '=' * 65)
        print('SCRIPT:', script)
        try:
            js = fetch(script)
        except Exception as exc:
            print('ERROR:', type(exc).__name__, str(exc)[:200])
            continue
        print('JS_CHARS:', len(js))
        # Find URL literals and nearby keyword context; never print secrets/tokens.
        urls = sorted(set(re.findall(r'https?://[^\s"\'`\\<>]{5,180}', js)))
        matches = [u for u in urls if KEYWORDS.search(u)]
        print('MATCHING URLS:', len(matches))
        for url in matches[:35]:
            print('URL:', url[:180])
        print('KEYWORD CONTEXT (up to 30):')
        count = 0
        for match in KEYWORDS.finditer(js):
            left = max(0, match.start() - 95)
            right = min(len(js), match.end() + 135)
            snippet = js[left:right].replace('\n', ' ').replace('\r', ' ')
            if len(snippet) > 260:
                snippet = snippet[:260]
            print('HINT:', snippet)
            count += 1
            if count >= 30:
                break
        print('KEYWORD CONTEXT PRINTED:', count)
    print('\nDONE. Share this log to identify an official news API, if exposed.')

if __name__ == '__main__':
    main()
