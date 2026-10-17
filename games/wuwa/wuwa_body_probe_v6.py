#!/usr/bin/env python3
"""Read-only WuWa official-news body discovery probe. Never writes events.json."""
import argparse
import datetime as dt
import html
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

BASE = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/jp'
JST = ZoneInfo('Asia/Tokyo')
DATE = r'20\d{2}\s*(?:年|[-/])\s*\d{1,2}\s*(?:月|[-/])\s*\d{1,2}\s*日?\s*\d{1,2}\s*[:：時]\s*\d{2}'
PAIR = re.compile(r'(' + DATE + r')\s*(?:~|～|〜|－|–|—|から|至|-)\s*(' + DATE + r')')
SINGLE = re.compile(DATE)
LABEL = re.compile(r'開催期間|イベント期間|実施期間|開放期間|開放時間|開催時間|挑戦期間|挑戦時間|期間限定|募集期間|投稿期間')
CHALLENGE = re.compile(r'逆境深塔|深塔|ホロタクティクス|無音区|戦歌復唱|千道門扉|危地任務|周期|リセット')
EXCLUDE = re.compile(r'メンテナンスのお知らせ|共鳴者・武器集音[（(]イベント[）)]|集音[（(]イベント[）)]')

def fetch(path):
    req = urllib.request.Request(BASE + path, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=22) as resp:
        return json.load(resp)

def plain(value):
    raw = str(value or '')
    raw = re.sub(r'<(?:br|/p|/div|/li)\b[^>]*>', ' ', raw, flags=re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', raw))).strip()

def published_at(row):
    try:
        raw = str(row.get('startTime', '')).replace('Z', '+00:00')
        value = dt.datetime.fromisoformat(raw)
        return value.replace(tzinfo=JST) if value.tzinfo is None else value.astimezone(JST)
    except (ValueError, TypeError):
        return None

def inspect(row):
    aid = str(row.get('articleId', ''))
    title = plain(row.get('articleTitle'))
    try:
        obj = fetch('/article/' + aid + '.json')
        body = plain(obj.get('articleContent', ''))
    except Exception as exc:
        return aid, title, None, str(exc)[:100]
    matches = []
    for m in PAIR.finditer(body):
        prefix = body[max(0, m.start()-160):m.start()]
        label = list(LABEL.finditer(prefix))
        if label:
            matches.append((m.group(1), m.group(2), prefix[-85:]))
    dates = [m.group(0) for m in SINGLE.finditer(body)]
    hints = []
    for m in LABEL.finditer(body):
        snippet = body[max(0, m.start()-30):m.end()+130]
        if len(hints) < 3 and snippet not in hints:
            hints.append(snippet)
    return aid, title, {'pairs': matches[:6], 'dates': dates[:6], 'hints': hints,
                         'challenge': bool(CHALLENGE.search(title + ' ' + body)),
                         'body_chars': len(body)}, None

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--days-back', type=int, default=120)
    p.add_argument('--limit', type=int, default=90, help='Maximum article bodies to inspect')
    p.add_argument('--workers', type=int, default=5)
    args = p.parse_args()
    rows = fetch('/MainMenu.json').get('article', [])
    now = dt.datetime.now(JST)
    by_id = {}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get('articleId', '')).isdigit():
            continue
        pub = published_at(row)
        if pub and pub >= now - dt.timedelta(days=args.days_back):
            by_id[str(row['articleId'])] = row
    ordered = sorted(by_id.values(), key=lambda x: published_at(x), reverse=True)
    eligible = [r for r in ordered if not EXCLUDE.search(plain(r.get('articleTitle')))]
    selected = eligible[:max(1, args.limit)]
    print('WUWA V6 BODY DISCOVERY / READ ONLY / NO FILE CHANGES')
    print('NEWS ROWS:', len(rows), 'RECENT UNIQUE:', len(ordered), 'ELIGIBLE:', len(eligible), 'CHECKING:', len(selected))
    if len(eligible) > len(selected):
        print('NOTE: scan capped; rerun with --limit', len(eligible), 'for full recent coverage')
    results = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 8))) as pool:
        futures = [pool.submit(inspect, r) for r in selected]
        for future in as_completed(futures):
            results.append(future.result())
    found = 0
    hinted = 0
    errors = 0
    for aid, title, info, err in sorted(results, key=lambda r: int(r[0]), reverse=True):
        if err:
            errors += 1
            print('FETCH ERROR:', aid, err)
            continue
        if info['pairs']:
            found += 1
            print('\nPERIOD CANDIDATE:', aid, title[:85], 'CHALLENGE:', info['challenge'])
            for start, end, context in info['pairs']:
                print(' RANGE:', start, '->', end, '| CONTEXT:', context)
        elif info['hints'] and info['dates']:
            hinted += 1
            if hinted <= 18:
                print('\nREVIEW DATES:', aid, title[:85], 'CHALLENGE:', info['challenge'])
                print(' DATES:', info['dates'])
                print(' LABEL:', info['hints'][0][:180])
        elif info['challenge'] and info['dates']:
            hinted += 1
            if hinted <= 18:
                print('\nCHALLENGE DATES:', aid, title[:85], 'DATES:', info['dates'])
    print('\nSUMMARY: PERIOD CANDIDATES:', found, 'OTHER DATE HINTS:', hinted, 'FETCH ERRORS:', errors)
    print('DONE: preview only; events.json unchanged. Dates are not automatically verified.')

if __name__ == '__main__':
    main()
