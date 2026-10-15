#!/usr/bin/env python3
"""Read-only diagnostic: match known HSR publisher ID plus certification.

This is a provisional publisher match, not independent authentication.
Never writes events.json; times are displayed as written, not converted.
"""
import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = 'https://bbs-api-os.hoyolab.com/community/post/wapi/'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json', 'Referer': 'https://www.hoyolab.com/'}
MAX_ARTICLES = 12
EXPECTED_UID = "172534910"
EXPECTED_CERT = "HonkaiSR Official"
DATE = re.compile(r'(?:20\d{2}\s*[-/.年]\s*)?\d{1,2}\s*[-/.月]\s*\d{1,2}\s*日?(?:\s*(?:\d{1,2}:\d{2}|アップデート後|after the (?:update|maintenance)))?', re.I)

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def handle_starttag(self, tag, attrs):
        if tag in ('br', 'p', 'div', 'li'):
            self.parts.append('\n')

def fetch(endpoint, params):
    url = BASE + endpoint + '?' + urlencode(params)
    with urlopen(Request(url, headers=HEADERS), timeout=20) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError('API response too large')
    result = json.loads(raw)
    if result.get('retcode') != 0:
        raise ValueError('API error: ' + str(result.get('message')))
    return result.get('data') or {}

def as_text(post):
    chunks = []
    structured = post.get('structured_content')
    if structured:
        try:
            blocks = json.loads(structured) if isinstance(structured, str) else structured
            if isinstance(blocks, list):
                chunks.extend(str(block.get('insert', '')) for block in blocks if isinstance(block, dict) and isinstance(block.get('insert'), str))
        except (ValueError, TypeError):
            pass
    if not chunks:
        parser = PlainText()
        parser.feed(str(post.get('content') or ''))
        chunks.append(''.join(parser.parts))
    return unescape('\n'.join(chunks))

def main():
    ids = {}
    for category in (1, 2, 3):
        try:
            data = fetch('getNewsList', {'gids': 6, 'type': category, 'page_size': 20})
            rows = data.get('list') or []
            print(f'Category {category}: {len(rows)} articles')
            for entry in rows:
                post = entry.get('post') or {}
                pid = str(post.get('post_id') or '')
                if pid.isdigit() and pid not in ids:
                    ids[pid] = post.get('subject') or '(no title)'
        except Exception as exc:
            print(f'WARNING: category {category}: {type(exc).__name__}: {exc}')
    print(f'Found {len(ids)} unique articles. Inspecting up to {MAX_ARTICLES}.')
    inspected = 0
    for pid, fallback_title in ids.items():
        if inspected >= MAX_ARTICLES:
            break
        try:
            data = fetch('getPostFull', {'post_id': pid})
            wrapper = data.get('post') or {}
            post = wrapper.get('post') or {}
            user = wrapper.get('user') or {}
            status = post.get('post_status') or {}
            inspected += 1
            title = str(post.get('subject') or fallback_title)
            cert = user.get('certification') or {}
            matched = (str(user.get('uid', '')) == EXPECTED_UID
                       and isinstance(cert, dict)
                       and cert.get('desc') == EXPECTED_CERT
                       and str(user.get('nickname', '')) == 'Honkai: Star Rail')
            if not matched:
                print(f'SKIP publisher mismatch: {title[:90]} (uid={user.get("uid")})')
                continue
            print(f'\nPUBLISHER MATCH (provisional): {title[:130]}')
            print(f'URL: https://www.hoyolab.com/article/{pid}')
            print(f'Publisher uid: {user.get("uid")}; certification: {cert.get("desc")}')
            body = as_text(post)
            print(f'Text length: {len(body)}')
            matches = list(DATE.finditer(body))
            for match in matches[:12]:
                context = ' '.join(body[max(0, match.start()-85):match.end()+110].split())
                print('  DATE CONTEXT (unconverted):', context[:240])
            if not matches:
                print('  No date-like text found; details may be in images.')
        except Exception as exc:
            print(f'WARNING: article {pid}: {type(exc).__name__}: {exc}')
    print(f'\nDone: {inspected} articles inspected. events.json unchanged.')
    print('Publisher match is provisional; do not auto-import without independent verification and event-specific date parsing.')

if __name__ == '__main__':
    main()
