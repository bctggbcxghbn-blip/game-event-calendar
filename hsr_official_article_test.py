#!/usr/bin/env python3
"""Read-only HoYoLAB HSR article/author diagnostic. Never edits events.json.

The API's absent post_status.is_official flag is NOT evidence of unofficial status.
Print author metadata for manual review; no article is auto-trusted.
"""
import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = 'https://bbs-api-os.hoyolab.com/community/post/wapi/'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json', 'Referer': 'https://www.hoyolab.com/'}
MAX_ARTICLES = 8
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
    print(f'Found {len(ids)} unique articles. Inspecting up to {MAX_ARTICLES}; none auto-verified.')
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
            print(f'\nARTICLE (NOT VERIFIED): {title[:130]}')
            print(f'URL: https://www.hoyolab.com/article/{pid}')
            print('post_status.is_official:', repr(status.get('is_official', 'MISSING')))
            print('author fields:', json.dumps({k: user.get(k) for k in ('uid', 'nickname', 'introduce', 'certification', 'certification_type', 'is_official') if k in user}, ensure_ascii=False)[:500])
            print('available author keys:', ', '.join(sorted(user.keys())[:35]))
            print('available wrapper keys:', ', '.join(sorted(wrapper.keys())[:25]))
            body = as_text(post)
            print('Text length:', len(body))
            for match in list(DATE.finditer(body))[:8]:
                context = ' '.join(body[max(0, match.start()-55):match.end()+65].split())
                print('  DATE CONTEXT:', context[:180])
        except Exception as exc:
            print(f'WARNING: article {pid}: {type(exc).__name__}: {exc}')
    print(f'\nDone: {inspected} articles inspected (not verified). events.json unchanged.')
    print('Do not auto-import until publisher identity is verified against an official account.')

if __name__ == '__main__':
    main()
