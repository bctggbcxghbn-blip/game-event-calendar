#!/usr/bin/env python3
"""WuWa official-news importer. Preview by default; --apply updates events.json.
No guessed dates: maintenance UTC+8 converted to JST; phase-one banner starts
use the announced maintenance end and are explicitly marked as planned.
"""
import argparse
import datetime as dt
import html
import json
import re
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/jp'
SITE = 'https://wutheringwaves.kurogames.com/jp/main/news/detail/'
JST = ZoneInfo('Asia/Tokyo')
UTC8 = dt.timezone(dt.timedelta(hours=8))
DATE = r'20\d{2}\s*(?:年|[-/])\s*\d{1,2}\s*(?:月|[-/])\s*\d{1,2}\s*日?\s*\d{1,2}\s*[:：時]\s*\d{2}'
PAIR = re.compile(r'(' + DATE + r')\s*(?:~|～|〜|－|–|—|から|至|-)\s*(' + DATE + r')')
SINGLE = re.compile(DATE)

def fetch(path):
    request = urllib.request.Request(BASE + path, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def plain(value):
    raw = str(value or '')
    raw = re.sub(r'<(?:br|/p|/div|/li)\b[^>]*>', ' ', raw, flags=re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', raw))).strip()

def parsedate(value, tz=JST):
    nums = re.findall(r'\d+', value)
    if len(nums) < 5:
        return None
    try:
        return dt.datetime(*map(int, nums[:5]), tzinfo=tz).astimezone(JST)
    except ValueError:
        return None

def version(title):
    match = re.search(r'Ver\.?\s*(\d+\.\d+)', title, re.I)
    return match.group(1) if match else None

def kind_of(title):
    if 'メンテナンスのお知らせ' in title:
        return 'maintenance'
    if re.search(r'共鳴者・武器集音[（(]イベント[）)]|集音[（(]イベント[）)]', title):
        return 'gacha'
    if re.search(r'イベント予告|イベント詳細|開催のお知らせ|イベント開催|イベントのお知らせ|ミニイベント|期間限定イベント|イベント情報', title):
        return 'event'
    if re.search(r'逆境深塔|深塔|ホロタクティクス|無音区|戦歌復唱|千道門扉|危地任務', title):
        return 'challenge'
    return None

def find_maintenance(body):
    # Look near the explicit maintenance label; do not accidentally use a compensation deadline.
    for label in re.finditer(r'メンテナンス日時|メンテナンス時間', body):
        segment = body[label.end():label.end()+180]
        match = PAIR.search(segment)
        if match:
            a, b = parsedate(match.group(1), UTC8), parsedate(match.group(2), UTC8)
            if a and b and a < b and (b-a).total_seconds() <= 24*3600:
                return a, b
    return None

def find_periods(body, kind, maintenance_end, ver):
    results = []
    # A single news post may list several banners. Keep unique intervals.
    for match in PAIR.finditer(body):
        before = body[max(0, match.start()-125):match.start()]
        if not re.search(r'開催期間|イベント期間|投稿期間|募集期間|開催時間|期間|集音|Duration', before):
            continue
        start, end = parsedate(match.group(1)), parsedate(match.group(2))
        if start and end and start < end and (end-start).days <= 120:
            results.append((start, end, 'explicit JST period'))
    if kind == 'gacha' and ver in maintenance_end:
        # Only if a duration label explicitly says the banner begins after the update.
        for label in re.finditer(r'開催期間', body):
            segment = body[label.end():label.end()+150]
            if not re.search(r'Ver\.?\s*\d+\.\d+\s*の?アップデート後|アップデート(?:終了)?後', segment):
                continue
            end_match = SINGLE.search(segment)
            if not end_match:
                continue
            start, end = maintenance_end[ver], parsedate(end_match.group(0))
            if start and end and start < end and (end-start).days <= 60:
                results.append((start, end, 'planned maintenance-end start'))
    return sorted(set(results))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--days-back', type=int, default=120)
    parser.add_argument('--events', default='events.json')
    args = parser.parse_args()
    now = dt.datetime.now(JST)
    rows = fetch('/MainMenu.json').get('article', [])
    unique = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        aid, title = str(row.get('articleId', '')), plain(row.get('articleTitle'))
        kind = kind_of(title)
        if not aid.isdigit() or not kind:
            continue
        try:
            published = dt.datetime.fromisoformat(row['startTime']).replace(tzinfo=JST)
        except (ValueError, KeyError, TypeError):
            continue
        if published < now - dt.timedelta(days=args.days_back):
            continue
        unique[aid] = (title, kind)
    print('WUWA V5', 'APPLY' if args.apply else 'PREVIEW / READ ONLY', 'ROWS:', len(rows), 'UNIQUE CANDIDATES:', len(unique))
    articles = {}
    for aid, (title, kind) in unique.items():
        try:
            data = fetch('/article/' + aid + '.json')
            articles[aid] = (title, kind, plain(data.get('articleContent', '')))
        except Exception as exc:
            print('FETCH ERROR:', aid, type(exc).__name__, str(exc)[:120])
    maintenance_end = {}
    found = []
    for aid, (title, kind, body) in articles.items():
        if kind != 'maintenance':
            continue
        period = find_maintenance(body)
        if not period:
            print('MAINTENANCE DATE NOT FOUND:', aid, title[:75]); continue
        start, end = period
        if version(title):
            maintenance_end[version(title)] = end
        found.append((aid, title, kind, start, end, 'official maintenance notice UTC+8 -> JST'))
    print('VERSION MAINTENANCE ENDS:', {k:v.strftime('%Y-%m-%d %H:%M') for k,v in maintenance_end.items()})
    for aid, (title, kind, body) in articles.items():
        if kind == 'maintenance':
            continue
        if kind == 'challenge':
            print('CHALLENGE REVIEW (no guessed dates):', aid, title[:75]); continue
        periods = find_periods(body, kind, maintenance_end, version(title))
        if not periods:
            print('SKIP NO VERIFIED PERIOD:', kind, aid, title[:75]); continue
        for start, end, basis in periods:
            found.append((aid, title, kind, start, end, basis))
    entries, seen = [], set()
    for aid, title, kind, start, end, basis in found:
        if end < now - dt.timedelta(days=1):
            continue
        key = (aid, kind, start.isoformat(), end.isoformat())
        if key in seen:
            continue
        seen.add(key)
        approx = 'planned' in basis
        entry = {
            'id': f'wuwa-official-{kind}-{aid}-{start:%Y%m%d%H%M}',
            'game': 'wuwa', 'name': title + ('（開始予定）' if approx else ''),
            'start': start.date().isoformat(), 'end': end.date().isoformat(),
            'kind': kind, 'source_status': 'official', 'official_url': SITE + aid,
            'start_time': start.strftime('%H:%M'), 'end_time': end.strftime('%H:%M'),
            'time_zone': 'Asia/Tokyo',
        }
        entries.append(entry)
        print('FOUND:', kind, aid, start.strftime('%Y-%m-%d %H:%M'), '->', end.strftime('%Y-%m-%d %H:%M'), basis, title[:70])
    print('EXTRACTED:', len(entries), 'BY KIND:', {k:sum(e['kind']==k for e in entries) for k in ('event', 'gacha', 'maintenance', 'challenge')})
    if not args.apply:
        print('PREVIEW ONLY: events.json unchanged. Do not enable --apply until dates are reviewed.'); return
    path = Path(args.events)
    existing = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(existing, list):
        raise ValueError('events.json must be a JSON array')
    ids = {e.get('id'): i for i, e in enumerate(existing) if isinstance(e, dict)}
    added = updated = 0
    for entry in entries:
        if entry['id'] in ids:
            if existing[ids[entry['id']]] != entry:
                existing[ids[entry['id']]] = entry; updated += 1
        else:
            existing.append(entry); added += 1
    if added or updated:
        path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('ADDED:', added, 'UPDATED:', updated)

if __name__ == '__main__':
    main()
