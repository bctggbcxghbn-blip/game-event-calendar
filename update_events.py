#!/usr/bin/env python3
"""Safely merge manually curated HTTPS JSON feeds and explicit-date RSS/Atom announcements."""
import datetime as dt
import hashlib
import json
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent
GAMES = {'genshin', 'wuwa', 'hsr', 'zzz', 'nte', 'arknights', 'endfield'}
DATE = r'(20\d{2})[年/.-](\d{1,2})[月/.-](\d{1,2})日?'
RANGE = re.compile(DATE + r'\s*(?:\([^)]*\)\s*)?(?:[〜～~–—－]|から|至|to)\s*' + DATE, re.I)

def valid(e):
    if not isinstance(e, dict) or e.get('game') not in GAMES:
        return False
    if any(not isinstance(e.get(k), str) or not e[k].strip() for k in ('id','name','start','end','kind')):
        return False
    try:
        return dt.date.fromisoformat(e['start']) <= dt.date.fromisoformat(e['end']) and len(e['id']) <= 180 and len(e['name']) <= 180 and (not e.get('url') or str(e['url']).startswith('https://'))
    except ValueError:
        return False

def download(url):
    if not isinstance(url, str) or urlparse(url).scheme != 'https':
        raise ValueError('HTTPS URL required')
    req = urllib.request.Request(url, headers={'User-Agent':'GameCalendarUpdater/2.0 (public feed reader)'})
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError('Feed exceeds 2 MB')
    return data

def get_text(node, names):
    for child in node.iter():
        if child.tag.split('}')[-1] in names and child.text:
            return child.text.strip()
    return ''

def rss_events(blob, config):
    root = ET.fromstring(blob)
    game = config['game']
    if game not in GAMES:
        raise ValueError('Unsupported game')
    result = []
    for item in root.iter():
        if item.tag.split('}')[-1] not in ('item', 'entry'):
            continue
        title = unescape(get_text(item, {'title'}))
        summary = re.sub('<[^>]*>', ' ', unescape(get_text(item, {'description', 'summary', 'content'})))
        # Require both dates to be explicit in the same title or paragraph.
        match = RANGE.search(title) or RANGE.search(summary)
        if not match or not title:
            continue
        try:
            start = dt.date(*map(int, match.groups()[:3]))
            end = dt.date(*map(int, match.groups()[3:]))
        except ValueError:
            continue
        if start > end or (end - start).days > 180:
            continue
        link = ''
        for child in item:
            if child.tag.split('}')[-1] == 'link':
                link = child.get('href') or (child.text or '').strip()
                break
        if link and not link.startswith('https://'):
            link = ''
        kind = 'イベント'
        if any(w in title for w in ('復刻', '復刻祈願', '復刻スカウト')):
            kind = '復刻'
        elif any(w in title for w in ('新キャラ', '新規キャラ', '新オペレーター')):
            kind = '新キャラ'
        elif any(w in title for w in ('ガチャ', '祈願', 'スカウト', '跳躍', '変調')):
            kind = 'ガチャ'
        uid = hashlib.sha256((game + '|' + link + '|' + title).encode()).hexdigest()[:20]
        e = {'id': 'feed-' + uid, 'game': game, 'name': title[:180], 'start': start.isoformat(), 'end': end.isoformat(), 'kind': kind, 'url': link, 'source_status': '自動抽出・要確認'}
        if valid(e):
            result.append(e)
    return result

def main():
    path = ROOT / 'events.json'
    current = json.loads(path.read_text(encoding='utf-8'))
    merged = {e['id']: e for e in current if valid(e)}
    config = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
    feeds = config.get('feeds', [])
    for feed in feeds:
        try:
            if isinstance(feed, str):
                url, mode = feed, 'json'
            elif isinstance(feed, dict):
                url, mode = feed['url'], feed.get('type', 'json')
            else:
                raise ValueError('Invalid feed entry')
            raw = download(url)
            if mode == 'json':
                rows = json.loads(raw)
                if not isinstance(rows, list):
                    raise ValueError('Expected JSON array')
            elif mode == 'rss':
                rows = rss_events(raw, feed)
            else:
                raise ValueError('Feed type must be json or rss')
            added = 0
            for e in rows:
                if valid(e):
                    merged[e['id']] = e
                    added += 1
            print(f'{url}: {added} valid events')
        except Exception as exc:
            print(f'WARNING: feed skipped ({feed}): {exc}')
    output = sorted(merged.values(), key=lambda e: (e['start'], e['game'], e['name']))
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(output)} total events; {len(feeds)} configured feeds')

if __name__ == '__main__':
    main()
