#!/usr/bin/env python3
"""V24: read-only official JP news ID/title discovery. Never edits events.json."""
import argparse
import datetime as dt
import html
import json
import re
import urllib.request

BASE = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/jp'
SITE = 'https://wutheringwaves.kurogames.com/jp/main/news/detail/'
KNOWN = {'5472', '5547', '5570'}
RULES = [
    ('MAINTENANCE', re.compile(r'メンテナンス|更新予告|アップデート(?:のお知らせ|予告)|バージョン更新', re.I)),
    ('GACHA', re.compile(r'集音|ピックアップ|共鳴者.{0,8}武器|キャラ.{0,8}ガチャ', re.I)),
    ('EVENT', re.compile(r'コンテンツ紹介|イベント(?:予告|紹介|詳細|開催|情報|のお知らせ)|期間限定|WEBイベント|ウェブイベント', re.I)),
    ('CHALLENGE', re.compile(r'逆境深塔|終焉マトリクス|死の歌が纏う海の廃墟|ホロタクティクス|挑戦コンテンツ', re.I)),
]

def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', str(s or '')))).strip()

def fetch(name):
    req = urllib.request.Request(BASE + '/' + name, headers={'User-Agent': 'Mozilla/5.0 (WuwaCalendarDiscovery/24)', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=25) as res:
        raw = res.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError('Index too large')
        return json.loads(raw)

def rows_from(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('article', 'articles', 'data', 'list'):
            if isinstance(data.get(key), list):
                return data[key]
            if isinstance(data.get(key), dict):
                nested = rows_from(data[key])
                if nested:
                    return nested
    return []

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=45, help='Maximum matched articles shown')
    p.add_argument('--days-back', type=int, default=120, help='Include recent articles and pinned known IDs')
    args = p.parse_args()
    print('WUWA V24 OFFICIAL ARTICLE DISCOVERY / READ ONLY')
    print('Only discovers article IDs/titles; DOES NOT import dates or edit events.json.')
    seen = {}
    for index in ('ArticleMenu.json', 'MainMenu.json'):
        try:
            rows = rows_from(fetch(index))
            print('INDEX:', index, 'ROWS:', len(rows))
        except Exception as e:
            print('INDEX ERROR:', index, type(e).__name__, str(e)[:160])
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            aid = str(row.get('articleId') or row.get('id') or '')
            title = clean(row.get('articleTitle') or row.get('title'))
            if not aid.isdigit() or not title:
                continue
            published = str(row.get('startTime') or row.get('publishTime') or row.get('createTime') or '')
            entry = {'id': aid, 'title': title, 'published': published}
            if aid not in seen or (published and not seen[aid]['published']):
                seen[aid] = entry
    if not seen:
        print('ERROR: No official index records found; check CDN format/access.')
        raise SystemExit(1)
    print('UNIQUE_ARTICLES:', len(seen))
    cutoff = dt.date.today() - dt.timedelta(days=max(0, args.days_back))
    matched = []
    for e in seen.values():
        categories = [label for label, rule in RULES if rule.search(e['title'])]
        if not categories:
            continue
        stamp = e['published'][:10]
        try:
            date = dt.date.fromisoformat(stamp)
        except ValueError:
            date = None
        if date is not None and date < cutoff and e['id'] not in KNOWN:
            continue
        e['categories'] = categories
        matched.append(e)
    matched.sort(key=lambda e: (e['published'], int(e['id'])), reverse=True)
    print('MATCHED:', len(matched), 'DISPLAY_LIMIT:', max(0, args.limit))
    for e in matched[:max(0, args.limit)]:
        print('ARTICLE:', e['id'], '|', '+'.join(e['categories']), '|', e['published'] or 'DATE_UNKNOWN', '|', e['title'][:105])
        print(' URL:', SITE + e['id'])
    for aid in sorted(KNOWN):
        e = seen.get(aid)
        print('KNOWN_CHECK:', aid, e['title'] if e else 'NOT_IN_INDEX')
    print('DONE. No files changed. Review classifications; title matches do not establish event dates.')

if __name__ == '__main__':
    main()
