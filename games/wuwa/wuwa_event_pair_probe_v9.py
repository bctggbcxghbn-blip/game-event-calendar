#!/usr/bin/env python3
"""WuWa V9: read-only event heading / period audit. Never writes events.json."""
import argparse
import datetime as dt
import html
import json
import re
import urllib.request

BASE = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/jp/article/'
DATE = r'20\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*\d{1,2}\s*[:：時]\s*\d{2}'
RANGE = re.compile(r'(' + DATE + r')\s*(?:~|～|〜|－|–|—|から|至|-)\s*(' + DATE + r')')
LABEL = re.compile(r'(?:✦\s*)?(?:開催期間|イベント期間|実施期間|開放期間|挑戦期間)(?:\s*✦)?\s*[:：]?')
HEADING = re.compile(r'(?P<prefix>(?:期間限定|ミニ|戦闘|探索|依頼|戦闘撮影|WEB|H5ウェブ|クライシス演習挑戦|7日間|潮汐の探り手|留まる影収集|【[^】]{1,30}】|\s|・|＆|\w){0,55}?(?:イベント|ログインボーナス|ログイン特典|特別調査|潮汐の探り手|ウェブイベント|WEBイベント)?\s*)[「『](?P<name>[^」』\n]{2,80})[」』]')
BAD_PREFIX = ('報酬', '星声', '衣装', 'アクセサリー', 'ストア')

def fetch(aid):
    req = urllib.request.Request(BASE + str(aid) + '.json', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)

def clean(raw):
    s = html.unescape(str(raw or ''))
    s = re.sub(r'<(?:br|/p|/div|/li|/h[1-6])\b[^>]*>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'[ \t\u3000]+', ' ', s)
    return re.sub(r'\n\s*\n+', '\n', s).strip()

def parse_date(value):
    numbers = re.findall(r'\d+', value)
    try:
        return dt.datetime(*map(int, numbers[:5]))
    except (TypeError, ValueError):
        return None

def get_heading(section):
    """Choose a section heading, not the last quoted noun in the description."""
    candidates = []
    for m in HEADING.finditer(section):
        prefix = m.group('prefix').strip()
        name = m.group('name').strip()
        # Require a recognizable event-type introduction, or a standalone quoted title.
        context = section[max(0, m.start()-45):m.start()].strip()
        pre = (context + ' ' + prefix).strip()
        signal = bool(re.search(r'イベント|ログイン|特別調査|潮汐の探り手|【WEB|【H5|戦闘|ミニ|期間限定', pre))
        if not signal or name.startswith(BAD_PREFIX):
            continue
        # Heading should be early in the section; reject quotes deep in explanatory prose.
        position = m.start()
        candidates.append((position, name, pre[-75:]))
    if not candidates:
        return None, 'no reliable heading'
    # The event heading generally precedes description, near the start of the section.
    pos, name, pre = candidates[0]
    return name, f'heading@{pos} ({pre})'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--article-ids', nargs='+', default=['5570', '5356', '5108'])
    args = ap.parse_args()
    print('WUWA V9 SECTION PAIRING / READ ONLY / NO FILE CHANGES')
    print('Server-time dates remain unconverted; UTC+8 dates converted to JST.')
    total = 0
    for aid in args.article_ids:
        article = fetch(aid)
        body = clean(article.get('articleContent'))
        labels = list(LABEL.finditer(body))
        print('\nARTICLE:', aid, clean(article.get('articleTitle')).replace('\n', ' '), 'LABELS:', len(labels))
        section_start = 0
        count = 0
        for i, label in enumerate(labels):
            next_start = labels[i+1].start() if i+1 < len(labels) else len(body)
            before = body[section_start:label.start()]
            after = body[label.end():next_start]
            match = RANGE.match(after.lstrip()[:140])
            name, method = get_heading(before)
            if not match:
                section_start = label.end()
                continue
            start, end = parse_date(match.group(1)), parse_date(match.group(2))
            if not start or not end or start >= end or (end-start).days > 120:
                section_start = label.end()
                continue
            suffix = after.lstrip()[match.end():match.end()+45]
            zone = 'UTC+8' if 'UTC+8' in suffix else ('サーバー時間' if 'サーバー時間' in suffix else '不明')
            if zone == 'UTC+8':
                start += dt.timedelta(hours=1)
                end += dt.timedelta(hours=1)
                zone = 'JST (converted UTC+8)'
            count += 1
            total += 1
            print('  PAIR', count, '|', name or 'REVIEW NAME', '|', start.strftime('%Y-%m-%d %H:%M'), '->', end.strftime('%Y-%m-%d %H:%M'), '|', zone)
            print('    METHOD:', method)
            if not name:
                print('    SECTION:', before[-210:].replace('\n', ' '))
            section_start = label.end()
        print('  EXPLICIT PERIODS:', count)
    print('\nTOTAL EXPLICIT PERIODS:', total)
    print('NO APPLY MODE. Do not register unverified names or server-time dates.')

if __name__ == '__main__':
    main()
