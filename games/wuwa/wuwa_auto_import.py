#!/usr/bin/env python3
"""Wuthering Waves official news importer. Preview by default; --apply writes events.json.
Only explicit dates in official article bodies are imported; no guessed schedules.
"""
import argparse
import datetime as dt
import html
import json
import re
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/jp'
SITE = 'https://wutheringwaves.kurogames.com/jp/main/news/detail/'
JST = ZoneInfo('Asia/Tokyo')
DATE = r'(20\d{2})\s*(?:年|[-/])\s*(\d{1,2})\s*(?:月|[-/])\s*(\d{1,2})\s*日?\s*(\d{1,2})\s*[:：時]\s*(\d{2})'
RANGE = re.compile(r'(' + DATE + r')\s*(?:~|～|〜|－|–|—|から|至)\s*(' + DATE + r')', re.I)
TAGS = re.compile(r'<[^>]*>')


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; EventCalendar/1.0)'})
    with urllib.request.urlopen(req, timeout=25) as res:
        return json.load(res)


def plain(s):
    s = re.sub(r'<(?:br|/p|/div|/li)\b[^>]*>', ' ', str(s or ''), flags=re.I)
    return re.sub(r'\s+', ' ', html.unescape(TAGS.sub(' ', s))).strip()


def stamp(groups, utc8=False):
    year, month, day, hour, minute = map(int, groups)
    zone = dt.timezone(dt.timedelta(hours=8)) if utc8 else JST
    return dt.datetime(year, month, day, hour, minute, tzinfo=zone).astimezone(JST)


def classify(title):
    if re.search(r'メンテナンスのお知らせ', title): return 'maintenance'
    if re.search(r'集音（イベント）|集音\(イベント\)|集音イベント', title): return 'gacha'
    if re.search(r'イベント予告|イベント詳細|開催のお知らせ|イベント開催|イベントのお知らせ', title): return 'event'
    if re.search(r'逆境深塔|深塔|ホロタクティクス|無音区|戦歌復唱|千道門扉', title): return 'challenge'
    return None


def get_rows(data):
    rows = data.get('article', []) if isinstance(data, dict) else []
    return rows if isinstance(rows, list) else []


def parse_period(text, category):
    # A date from the announcement publication or its 2099 sentinel is never an event date.
    if category == 'maintenance':
        m = re.search(r'メンテナンス日時.{0,40}?(' + DATE + r')\s*(?:~|～|〜|－|–|—)\s*(' + DATE + r')', text)
        if not m: return None
        a, b = stamp(m.groups()[1:6], True), stamp(m.groups()[7:12], True)
        return a, b, 'maintenance UTC+8'
    # For event/gacha, only match a clearly labelled period near the two timestamps.
    for m in RANGE.finditer(text):
        preceding = text[max(0, m.start()-95):m.start()]
        if not re.search(r'開催期間|イベント期間|期間|開催時間', preceding): continue
        a, b = stamp(m.groups()[1:6]), stamp(m.groups()[7:12])
        if b > a and (b-a).days < 120: return a, b, 'explicit JST range'
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', help='Write verified entries to events.json')
    p.add_argument('--days-back', type=int, default=45)
    p.add_argument('--limit', type=int, default=180)
    p.add_argument('--events', default='events.json')
    args = p.parse_args()
    now = dt.datetime.now(JST)
    cutoff = now - dt.timedelta(days=args.days_back)
    print('WUWA OFFICIAL AUTO IMPORT', 'APPLY' if args.apply else 'PREVIEW / READ ONLY')
    rows = get_rows(fetch(ROOT + '/MainMenu.json'))
    print('NEWS ROWS:', len(rows))
    candidates = []
    for row in rows:
        if not isinstance(row, dict): continue
        title = plain(row.get('articleTitle'))
        category = classify(title)
        if not category: continue
        try:
            published = dt.datetime.fromisoformat(str(row.get('startTime', ''))).replace(tzinfo=JST)
            if published < cutoff: continue
        except ValueError: continue
        candidates.append((row, title, category))
    candidates.sort(key=lambda x: str(x[0].get('startTime', '')), reverse=True)
    print('CANDIDATES:', len(candidates), 'CHECKING:', min(len(candidates), args.limit))
    new = []
    counts = {'event':0,'gacha':0,'maintenance':0,'challenge':0}
    for row, title, category in candidates[:args.limit]:
        aid = row.get('articleId')
        if not str(aid).isdigit(): continue
        try:
            body = fetch(f'{ROOT}/article/{aid}.json')
        except Exception as e:
            print('FETCH FAILED:', aid, type(e).__name__)
            continue
        content = plain(body.get('articleContent', '')) if isinstance(body, dict) else ''
        if category == 'challenge':
            counts['challenge'] += 1
            print('CHALLENGE NEEDS REVIEW:', aid, title)
            continue
        period = parse_period(content, category)
        if not period:
            print('NO EXPLICIT FULL PERIOD:', category, aid, title)
            continue
        start, end, basis = period
        if end < now - dt.timedelta(days=1): continue
        entry = {
            'id': f'wuwa-official-{category}-{aid}',
            'game': 'wuwa',
            'name': title,
            'start': start.date().isoformat(),
            'end': end.date().isoformat(),
            'kind': category,
            'source_status': 'official',
            'official_url': SITE + str(aid),
            'start_time': start.strftime('%H:%M'),
            'end_time': end.strftime('%H:%M'),
            'time_zone': 'Asia/Tokyo',
        }
        counts[category] += 1
        new.append(entry)
        print('FOUND:', category, title, start.strftime('%Y-%m-%d %H:%M'), '->', end.strftime('%Y-%m-%d %H:%M'), basis)
    print('EXTRACTED:', counts, 'TOTAL:', len(new))
    if not args.apply:
        print('PREVIEW ONLY: events.json unchanged. Run with --apply after checking dates.')
        return
    path = Path(args.events)
    events = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(events, list): raise ValueError('events.json must contain a list')
    by_id = {e.get('id'):i for i,e in enumerate(events) if isinstance(e,dict)}
    added = updated = 0
    for e in new:
        if e['id'] in by_id:
            if events[by_id[e['id']]] != e:
                events[by_id[e['id']]] = e
                updated += 1
        else:
            events.append(e)
            added += 1
    if added or updated:
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('ADDED:', added, 'UPDATED:', updated, 'UNCHANGED:', len(new)-added-updated)


if __name__ == '__main__':
    main()
