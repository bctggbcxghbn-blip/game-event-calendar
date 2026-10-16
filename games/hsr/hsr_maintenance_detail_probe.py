#!/usr/bin/env python3
"""Read-only test of HoYoLAB HSR maintenance announcement body and dates.

Does not change events.json. Endpoints are undocumented and may change.
"""
import datetime as dt
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

BASE = 'https://bbs-api-os.hoyolab.com'
LIST = BASE + '/community/post/wapi/getNewsList'
DETAIL = BASE + '/community/post/wapi/getPostFull'
PARAMS = {'gids': '6', 'type': '1', 'page_size': '20'}
MAX_BYTES = 2_000_000

class StripHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

def get_json(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; GameEventCalendar/1.0)',
        'Accept': 'application/json',
        'Referer': 'https://www.hoyolab.com/',
    })
    with urllib.request.urlopen(req, timeout=15) as res:
        raw = res.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Response too large')
    obj = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(obj, dict) or obj.get('retcode') != 0:
        raise ValueError(f'API error: {str(obj.get("message") if isinstance(obj, dict) else obj)[:100]}')
    return obj.get('data')

def plain(raw):
    parser = StripHTML()
    parser.feed(html.unescape(raw))
    return re.sub(r'\s+', ' ', html.unescape(' '.join(parser.parts))).strip()

def main():
    print('Read-only HSR official announcement detail probe', flush=True)
    try:
        data = get_json(LIST + '?' + urllib.parse.urlencode(PARAMS))
        items = data.get('list', []) if isinstance(data, dict) else []
        matches = []
        for item in items:
            post = item.get('post', item) if isinstance(item, dict) else {}
            if not isinstance(post, dict):
                continue
            title = str(post.get('subject') or post.get('title') or '')
            if re.search(r'(?:update and maintenance notice|maintenance notice|维护公告|维护预告)', title, re.I):
                pid = post.get('post_id') or post.get('id')
                if pid is not None and str(pid).isdigit():
                    matches.append((str(pid), title))
        print(f'Announcement candidates in first {len(items)} articles: {len(matches)}', flush=True)
        for pid, title in matches[:3]:
            print(f'\nARTICLE: {title} | post_id={pid}', flush=True)
            print(f'Link: https://www.hoyolab.com/article/{pid}', flush=True)
            try:
                detail = get_json(DETAIL + '?' + urllib.parse.urlencode({'post_id': pid}))
                if not isinstance(detail, dict):
                    print('WARNING: unexpected detail structure')
                    continue
                post = detail.get('post', {})
                if not isinstance(post, dict):
                    print('WARNING: missing post object')
                    continue
                content = post.get('content') or post.get('post', {}).get('content', '') if isinstance(post.get('post'), dict) else post.get('content', '')
                if not isinstance(content, str):
                    content = json.dumps(content, ensure_ascii=False)
                try:
                    decoded = json.loads(content)
                    if isinstance(decoded, dict):
                        content = json.dumps(decoded, ensure_ascii=False)
                except (ValueError, TypeError):
                    pass
                text = plain(content)
                print(f'Detail text length: {len(text)}', flush=True)
                for term in ('Maintenance', 'Update Time', 'UTC+8', 'UTC +8', 'server', '2026/'):
                    m = re.search(re.escape(term), text, re.I)
                    if m:
                        print(f'Context [{term}]: {text[max(0,m.start()-110):m.end()+260]}', flush=True)
                timestamps = re.findall(r'20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?', text)
                print(f'Date/time strings (not yet verified): {timestamps[:12]}', flush=True)
                if not text:
                    print('WARNING: empty text; inspect detail response structure before implementing parsing')
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
                print(f'WARNING: detail fetch failed: {type(exc).__name__}: {str(exc)[:180]}', flush=True)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'WARNING: list fetch failed: {type(exc).__name__}: {str(exc)[:180]}', flush=True)
    print('\nProbe complete. No files modified.', flush=True)

if __name__ == '__main__':
    main()
