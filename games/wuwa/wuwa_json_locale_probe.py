#!/usr/bin/env python3
"""Read-only discovery of official Wuthering Waves news JSON."""
import json
import re
import urllib.error
import urllib.request

ROOTS = [
    'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152',
    'https://media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152',
]
KEYWORDS = {
    'EVENT': ['イベント', 'event', '活動'],
    'GACHA': ['集音', '共鳴者', '武器', 'convene', 'banner', 'ガチャ', '唤取'],
    'MAINTENANCE': ['メンテナンス', 'アップデート', 'maintenance', 'update', '停机维护'],
    'CHALLENGE': ['逆境深塔', 'ホロタクティクス', 'tower of adversity', 'whimpering wastes', '深境'],
}

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; CalendarNewsProbe/1.0)', 'Accept': 'application/json,*/*'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read(3_000_000)
            print('HTTP:', resp.status, 'BYTES:', len(data))
            return json.loads(data.decode('utf-8-sig'))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, UnicodeError, json.JSONDecodeError) as exc:
        print('ERROR:', type(exc).__name__, str(exc)[:200])
        return None

def inspect(data):
    if isinstance(data, dict):
        print('ROOT KEYS:', list(data)[:25])
        articles = data.get('article')
        if isinstance(articles, list):
            print('ARTICLE COUNT:', len(articles))
            for a in articles[:3]:
                if isinstance(a, dict):
                    print('ARTICLE SAMPLE:', json.dumps({k:v for k,v in a.items() if k.lower() in ('id','title','name','starttime','endtime','articletype')}, ensure_ascii=False)[:350])
    elif isinstance(data, list):
        print('LIST COUNT:', len(data))
    serialized = json.dumps(data, ensure_ascii=False)
    for label, words in KEYWORDS.items():
        found = [w for w in words if w.casefold() in serialized.casefold()]
        print(f'{label} KEYWORDS:', ', '.join(found) if found else 'none')
    if isinstance(data, dict) and isinstance(data.get('article'), list):
        for a in data['article'][:300]:
            if not isinstance(a, dict):
                continue
            title = str(a.get('title') or a.get('name') or '')
            matches = [label for label, words in KEYWORDS.items() if any(w.casefold() in title.casefold() for w in words)]
            if matches:
                print('MATCH:', ','.join(matches), '|', title[:100], '| ID:', a.get('id'), '| START:', a.get('startTime'))

print('WUWA OFFICIAL LOCALE JSON PROBE / READ ONLY')
print('events.json will NOT be changed.')
for root in ROOTS:
    for locale in ('jp', 'en'):
        for filename in ('MainMenu.json', 'ArticleMenu.json'):
            url = f'{root}/{locale}/{filename}'
            print('\n' + '=' * 65)
            print('TRY:', url)
            data = get(url)
            if data is not None:
                inspect(data)
print('\nDONE. Share this log.')
