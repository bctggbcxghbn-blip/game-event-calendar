#!/usr/bin/env python3
"""Read-only diagnostic: discover HSR news through HoYoLAB's community API.

Never modifies events.json. API availability and schema can change.
"""
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList'
GAME_ID = 6  # HSR in HoYoLAB's news API

def main():
    total = 0
    for category, kind in [(1, 'notices'), (2, 'events'), (3, 'info')]:
        url = API + '?' + urlencode({'gids': GAME_ID, 'type': category, 'page_size': 20})
        print(f'Checking {kind} ...')
        try:
            request = Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json',
                'Referer': 'https://www.hoyolab.com/',
            })
            with urlopen(request, timeout=20) as response:
                raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ValueError('Response exceeds 1 MB')
            result = json.loads(raw)
            if result.get('retcode') != 0:
                print(f'  API returned retcode={result.get("retcode")}, message={result.get("message")}')
                continue
            rows = (result.get('data') or {}).get('list') or []
            print(f'  {len(rows)} entries returned')
            for entry in rows[:10]:
                post = entry.get('post') or {}
                post_id = str(post.get('post_id') or '')
                title = str(post.get('subject') or '').replace('\n', ' ')[:110]
                official = (post.get('post_status') or {}).get('is_official')
                if post_id and title:
                    print(f'  [{"official" if official else "unverified"}] {title} | https://www.hoyolab.com/article/{post_id}')
                    total += 1
        except Exception as exc:
            print(f'  WARNING: {type(exc).__name__}: {exc}')
    print(f'HSR HoYoLAB discovery diagnostic: {total} articles displayed; events.json unchanged.')
    if not total:
        print('No articles retrieved. API may be unavailable, blocked, or changed; existing importers remain intact.')

if __name__ == '__main__':
    main()
