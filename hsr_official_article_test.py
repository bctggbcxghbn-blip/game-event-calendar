#!/usr/bin/env python3
"""Read-only diagnostic for HSR HoYoLAB official article text and date snippets.

Does NOT modify events.json. Does NOT infer dates or create events.
"""
import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = 'https://bbs-api-os.hoyolab.com/community/post/wapi/'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json', 'Referer': 'https://www.hoyolab.com/'}
MAX_ARTICLES = 6
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
        raw = str(post.get('content') or '')
        parser = PlainText()
        parser.feed(raw)
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
                if pid.isdigit():
                    ids[pid] = post.get('subject') or '(no title)'
        except Exception as exc:
            print(f'WARNING: category {category}: {type(exc).__name__}: {exc}')
    print(f'Found {len(ids)} unique articles. Checking up to {MAX_ARTICLES} verified official articles.')
    checked = 0
    for pid, fallback_title in ids.items():
        if checked >= MAX_ARTICLES:
            break
        try:
            data = fetch('getPostFull', {'post_id': pid})
            wrapper = data.get('post') or {}
            post = wrapper.get('post') or {}
            status = post.get('post_status') or {}
            # Only an explicit True counts as official; absence is not proof.
            if status.get('is_official') is not True:
                print(f'SKIP unverified: {fallback_title[:75]}')
                continue
            checked += 1
            title = str(post.get('subject') or fallback_title)
            body = as_text(post)
            print(f'\nOFFICIAL: {title[:130]}')
            print(f'URL: https://www.hoyolab.com/article/{pid}')
            print(f'Text length: {len(body)} characters')
            matches = list(DATE.finditer(body))
            if not matches:
                print('  No date-like expressions in available text (dates may be in images).')
            for match in matches[:12]:
                context = ' '.join(body[max(0, match.start()-55):match.end()+65].split())
                print('  DATE CONTEXT: ' + context[:180])
            if len(matches) > 12:
                print(f'  ... and {len(matches)-12} more matches')
        except Exception as exc:
            print(f'WARNING: article {pid}: {type(exc).__name__}: {exc}')
    print(f'\nDone: {checked} verified official articles inspected. events.json unchanged.')
    if not checked:
        print('No articles with an explicit official flag found. Do not auto-import from these results.')

if __name__ == '__main__':
    main()
