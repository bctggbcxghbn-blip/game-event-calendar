#!/usr/bin/env python3
"""Official Wuthering Waves calendar importer. Preview by default; --apply writes events.json.
Only explicit Japanese dates or version-relative starts tied to announced maintenance are used.
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
DATE = r'20\d{2}\s*(?:年|[-/])\s*\d{1,2}\s*(?:月|[-/])\s*\d{1,2}\s*日?\s*\d{1,2}\s*[:：時]\s*\d{2}'
PAIR = re.compile(r'(' + DATE + r')\s*(?:~|～|〜|－|–|—|から|至)\s*(' + DATE + r')')
SINGLE = re.compile(DATE)

def fetch(path):
    req = urllib.request.Request(ROOT + path, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def plain(s):
    s = re.sub(r'<(?:br|/p|/div|/li)\b[^>]*>', ' ', str(s or ''), flags=re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', s))).strip()

def date(s, utc8=False):
    parts = re.findall(r'\d+', s)
    if len(parts) < 5: return None
    zone = dt.timezone(dt.timedelta(hours=8)) if utc8 else JST
    try:
        return dt.datetime(*map(int, parts[:5]), tzinfo=zone).astimezone(JST)
    except ValueError:
        return None

def version(title):
    m = re.search(r'Ver\.?\s*(\d+\.\d+)', title, re.I)
    return m.group(1) if m else None

def classify(title):
    if 'メンテナンスのお知らせ' in title: return 'maintenance'
    if re.search(r'共鳴者・武器集音（イベント）|共鳴者・武器集音\(イベント\)', title): return 'gacha'
    if re.search(r'イベント予告|イベント詳細|開催のお知らせ|イベント開催|イベントのお知らせ|ミニイベント|期間限定イベント', title): return 'event'
    if re.search(r'逆境深塔|深塔|ホロタクティクス|無音区|戦歌復唱|千道門扉', title): return 'challenge'
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--days-back', type=int, default=90)
    parser.add_argument('--events', default='events.json')
    args = parser.parse_args()
    now = dt.datetime.now(JST)
    rows = fetch('/MainMenu.json').get('article', [])
    print('WUWA V4', 'APPLY' if args.apply else 'PREVIEW / READ ONLY', 'ROWS:', len(rows))
    unique = {}
    for row in rows:
        if not isinstance(row, dict): continue
        aid = str(row.get('articleId', ''))
        title = plain(row.get('articleTitle'))
        kind = classify(title)
        if not aid.isdigit() or not kind: continue
        try: pub = dt.datetime.fromisoformat(row['startTime']).replace(tzinfo=JST)
        except (ValueError, KeyError, TypeError): continue
        if pub < now - dt.timedelta(days=args.days_back): continue
        unique[aid] = (title, kind)
    print('UNIQUE CANDIDATES:', len(unique))
    articles = {}
    for aid, (title, kind) in unique.items():
        try:
            data = fetch('/article/' + aid + '.json')
            articles[aid] = (title, kind, plain(data.get('articleContent', '')))
        except Exception as exc:
            print('FETCH ERROR:', aid, type(exc).__name__)
    maintenance = {}
    extracted = []
    for aid, (title, kind, body) in articles.items():
        if kind != 'maintenance': continue
        marker = re.search(r'メンテナンス日時.{0,160}', body)
        match = PAIR.search(marker.group(0)) if marker else None
        if not match: print('SKIP MAINTENANCE NO PAIR:', aid); continue
        start, end = date(match.group(1), True), date(match.group(2), True)
        if not start or not end or end <= start: continue
        if version(title): maintenance[version(title)] = end
        extracted.append((aid, title, kind, start, end, 'UTC+8 converted to JST'))
    print('VERSION MAINTENANCE ENDS:', {k:v.strftime('%Y-%m-%d %H:%M') for k,v in maintenance.items()})
    for aid, (title, kind, body) in articles.items():
        if kind == 'maintenance': continue
        if kind == 'challenge':
            print('CHALLENGE REVIEW (no inferred cycle):', aid, title[:80]); continue
        periods = []
        for match in PAIR.finditer(body):
            before = body[max(0, match.start()-110):match.start()]
            if not re.search(r'開催期間|イベント期間|投稿期間|募集期間|開催時間|期間|Duration', before): continue
            start, end = date(match.group(1)), date(match.group(2))
            if start and end and start < end and (end-start).days <= 120:
                periods.append((start, end, 'explicit JST range'))
        if not periods and kind == 'gacha' and version(title) in maintenance and re.search(r'アップデート(?:終了)?後', body):
            # End date must appear near an explicitly labeled event duration.
            marker = re.search(r'開催期間.{0,160}', body)
            match = SINGLE.search(marker.group(0)) if marker else None
            if match:
                start, end = maintenance[version(title)], date(match.group(0))
                if end and start < end and (end-start).days <= 60:
                    periods.append((start, end, 'planned maintenance end (approximate start)'))
        if not periods:
            print('SKIP NO VERIFIED PERIOD:', kind, aid, title[:85]); continue
        # Multiple banners within a single announcement may have distinct periods.
        # Deduplicate identical ranges; create one record per distinct interval.
        for index, (start, end, basis) in enumerate(sorted(set(periods)), 1):
            extracted.append((aid, title, kind, start, end, basis))
    entries = []
    seen = set()
    for aid, title, kind, start, end, basis in extracted:
        if end < now - dt.timedelta(days=1): continue
        key = (aid, kind, start.isoformat(), end.isoformat())
        if key in seen: continue
        seen.add(key)
        suffix = start.strftime('%Y%m%d%H%M')
        entry = {
            'id': f'wuwa-official-{kind}-{aid}-{suffix}',
            'game': 'wuwa', 'name': title,
            'start': start.date().isoformat(), 'end': end.date().isoformat(),
            'kind': kind, 'source_status': 'official', 'official_url': SITE + aid,
            'start_time': start.strftime('%H:%M'), 'end_time': end.strftime('%H:%M'),
            'time_zone': 'Asia/Tokyo',
        }
        if 'approximate' in basis:
            entry['name'] += '（開始予定）'
        entries.append(entry)
        print('FOUND:', kind, aid, start.strftime('%Y-%m-%d %H:%M'), '->', end.strftime('%Y-%m-%d %H:%M'), basis, title[:70])
    print('EXTRACTED:', len(entries), 'BY KIND:', {k:sum(e['kind']==k for e in entries) for k in ('event','gacha','maintenance','challenge')})
    if not args.apply:
        print('PREVIEW ONLY. events.json unchanged. Verify dates before --apply.'); return
    path = Path(args.events)
    existing = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(existing, list): raise ValueError('events.json must be a JSON array')
    ids = {e.get('id'):i for i,e in enumerate(existing) if isinstance(e,dict)}
    added = updated = 0
    for entry in entries:
        if entry['id'] in ids:
            if existing[ids[entry['id']]] != entry:
                existing[ids[entry['id']]] = entry; updated += 1
        else:
            existing.append(entry); added += 1
    if added or updated:
        path.write_text(json.dumps(existing, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('ADDED:', added, 'UPDATED:', updated)

if __name__ == '__main__': main()
