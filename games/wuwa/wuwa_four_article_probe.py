#!/usr/bin/env python3
"""Read-only Wuthering Waves official news article inspection."""
import json
import re
import urllib.request
from urllib.error import HTTPError, URLError

ROOT = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152'
CATEGORIES = {
    'EVENT': ['イベント', 'event', 'イベント情報', '期間限定'],
    'GACHA': ['集音', 'convene', '共鳴者', '武器集音'],
    'MAINTENANCE': ['メンテナンス', 'maintenance', 'アップデート', 'version update'],
    'CHALLENGE': ['ホロタクティクス', '逆境深塔', '深塔', 'whimpering wastes', 'tower of adversity', 'tactical hologram'],
}
DATE_RE = re.compile(r'(?:20\d{2}[年/.-]\s*\d{1,2}[月/.-]\s*\d{1,2}日?|\d{1,2}[月/.-]\s*\d{1,2}日?|\b\w+\s+\d{1,2},?\s+20\d{2}\b|\d{1,2}:\d{2})', re.I)

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; CalendarResearch/1.0)'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)

def flatten(value, depth=0):
    if depth > 12:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return ' '.join(flatten(v, depth + 1) for v in value.values())
    if isinstance(value, list):
        return ' '.join(flatten(v, depth + 1) for v in value[:100])
    return ''

def clean(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip()

def articles(data):
    if isinstance(data, dict):
        for key in ('article', 'articles', 'list', 'data'):
            if isinstance(data.get(key), list):
                return data[key]
    if isinstance(data, list):
        return data
    return []

def article_id(row):
    for key in ('articleId', 'articleID', 'id', 'article_id'):
        value = row.get(key)
        if value is not None and str(value).isdigit():
            return str(value)
    return None

print('WUWA FOUR-CATEGORY ARTICLE PROBE / READ ONLY')
print('events.json will NOT be changed.')
for locale in ('jp', 'en'):
    print('\n' + '=' * 65)
    print('LOCALE:', locale)
    try:
        menu = fetch(f'{ROOT}/{locale}/MainMenu.json')
    except (HTTPError, URLError, ValueError, TimeoutError) as e:
        print('FETCH ERROR:', repr(e))
        continue
    rows = articles(menu)
    print('TOTAL ROWS:', len(rows))
    print('SAMPLE KEYS:', list(rows[0]) if rows and isinstance(rows[0], dict) else 'none')
    seen_ids = set()
    for category, terms in CATEGORIES.items():
        found = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            summary = clean(flatten(row)).lower()
            if any(t.lower() in summary for t in terms):
                found.append(row)
        found.sort(key=lambda x: str(x.get('startTime', '')), reverse=True)
        print(f'\n{category}: {len(found)} matching rows')
        inspected = 0
        for row in found:
            aid = article_id(row)
            if not aid or aid in seen_ids:
                continue
            seen_ids.add(aid)
            title = clean(str(row.get('title') or row.get('articleTitle') or row.get('name') or ''))
            print(' ARTICLE:', aid, 'DATE:', row.get('startTime'), 'TITLE:', title[:130])
            print(' URL:', f'https://wutheringwaves.kurogames.com/{locale}/main/news/detail/{aid}')
            try:
                body = fetch(f'{ROOT}/{locale}/article/{aid}.json')
                body_text = clean(flatten(body))
                print(' BODY KEYS:', list(body)[:15] if isinstance(body, dict) else type(body).__name__)
                print(' BODY CHARS:', len(body_text))
                print(' BODY SAMPLE:', body_text[:500])
                print(' DATE/TIME SAMPLES:', DATE_RE.findall(body_text)[:15])
            except (HTTPError, URLError, ValueError, TimeoutError) as e:
                print(' ARTICLE ERROR:', repr(e))
            inspected += 1
            if inspected >= 3:
                break
        if inspected == 0:
            print(' NO ARTICLES WITH USABLE ID; SAMPLE:', json.dumps(found[:1], ensure_ascii=False)[:600])
print('\nDONE. Share this log. No files were changed.')
