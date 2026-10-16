#!/usr/bin/env python3
"""Read-only connectivity test for unofficially documented HoYoLAB news endpoints.

Does not modify events.json or any repository file. The endpoints may change.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

SOURCES = [
    ('HoYoLAB global', 'https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList'),
    ('Miyoushe China', 'https://bbs-api.miyoushe.com/post/wapi/getNewsList'),
]
PARAMS = {'gids': '6', 'type': '1', 'page_size': '20'}
KEYWORDS = ('maintenance', 'update notice', 'update and maintenance', '维护', '停机', 'メンテナンス')


def probe(label, endpoint):
    url = endpoint + '?' + urllib.parse.urlencode(PARAMS)
    print(f'\nSOURCE: {label}', flush=True)
    print(f'API: {url}', flush=True)
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; GameEventCalendar/1.0)',
        'Accept': 'application/json',
        'Referer': 'https://www.hoyolab.com/' if 'os.hoyolab' in endpoint else 'https://www.miyoushe.com/',
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            payload = response.read(1_000_001)
            print(f'HTTP status: {response.status}', flush=True)
        if len(payload) > 1_000_000:
            print('WARNING: response too large; skipped')
            return
        result = json.loads(payload.decode('utf-8-sig'))
        if not isinstance(result, dict):
            print('WARNING: unexpected JSON structure')
            return
        print(f'API retcode: {result.get("retcode")} | message: {str(result.get("message", ""))[:120]}')
        data = result.get('data')
        entries = data.get('list', []) if isinstance(data, dict) else []
        if not isinstance(entries, list):
            print('WARNING: data.list is not an array')
            return
        print(f'Articles returned: {len(entries)}')
        for item in entries[:20]:
            if not isinstance(item, dict):
                continue
            post = item.get('post', item)
            if not isinstance(post, dict):
                continue
            title = str(post.get('subject') or post.get('title') or '').strip()
            post_id = post.get('post_id') or post.get('id')
            if title:
                matched = any(word in title.lower() for word in KEYWORDS)
                flag = 'MAINTENANCE CANDIDATE' if matched else 'article'
                print(f'  {flag}: {title[:110]} | post_id={post_id}')
        print('NOTE: A title match is not a verified maintenance schedule.')
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'WARNING: API unavailable: {type(exc).__name__}: {str(exc)[:180]}')


def main():
    for label, endpoint in SOURCES:
        probe(label, endpoint)
    print('\nProbe complete. No files modified.')


if __name__ == '__main__':
    main()
