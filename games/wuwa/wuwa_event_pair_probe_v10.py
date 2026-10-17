#!/usr/bin/env python3
"""WuWa V10: cautious official event name/date pairing, read-only."""
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
# Match event headings ONLY (not arbitrary quoted nouns in explanatory text).
HEADING = re.compile(r'(?:期間限定[^\n「」]{0,30}?イベント|ミニイベント|戦闘イベント|戦闘撮影イベント|探索イベント|依頼イベント|WEBイベント|ウェブイベント|H5ウェブイベント|7日間ログイン(?:ボーナス|イベント)|期間限定ログインボーナス|留まる影収集イベント|クライシス演習挑戦イベント|潮汐の探り手|(?:イベント|ログインボーナス))\s*[「『](?P<name>[^」』\n]{2,80})[」』]')
# Some official titles are written without the word event immediately before the quote.
HEADING_ALT = re.compile(r'(?m)^\s*(?:【WEBイベント】\s*)?[「『](?P<name>[^」』\n]{2,80})[」』]\s*$')


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


def parsedate(value):
    try:
        return dt.datetime(*map(int, re.findall(r'\d+', value)[:5]))
    except (ValueError, TypeError):
        return None


def heading(before):
    matches = list(HEADING.finditer(before))
    if matches:
        m = matches[-1]
        return m.group('name').strip(), 'explicit event heading'
    # Deliberately do not fall back to the nearest arbitrary quote.
    return None, 'REVIEW: no explicit event heading'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--article-ids', nargs='+', default=['5570', '5356', '5108'])
    args = ap.parse_args()
    print('WUWA V10 HEADING PAIRING / READ ONLY / NO FILE CHANGES')
    print('Server time is NOT converted. Only explicitly UTC+8 periods are converted to JST.')
    total = named = uncertain = 0
    for aid in args.article_ids:
        article = fetch(aid)
        body = clean(article.get('articleContent'))
        labels = list(LABEL.finditer(body))
        print('\nARTICLE:', aid, clean(article.get('articleTitle')).replace('\n', ' '))
        section_start = 0
        count = 0
        for i, label in enumerate(labels):
            next_start = labels[i+1].start() if i+1 < len(labels) else len(body)
            before = body[section_start:label.start()]
            after = body[label.end():next_start]
            m = RANGE.match(after.lstrip()[:150])
            if not m:
                section_start = label.end()
                continue
            start, end = parsedate(m.group(1)), parsedate(m.group(2))
            if not start or not end or start >= end or (end-start).days > 120:
                section_start = label.end()
                continue
            name, method = heading(before)
            suffix = after.lstrip()[m.end():m.end()+60]
            zone = 'UTC+8' if 'UTC+8' in suffix else ('サーバー時間' if 'サーバー時間' in suffix else '不明')
            if zone == 'UTC+8':
                start += dt.timedelta(hours=1)
                end += dt.timedelta(hours=1)
                zone = 'JST (UTC+8 +1h)'
            count += 1
            total += 1
            named += bool(name)
            uncertain += zone in ('サーバー時間', '不明')
            print(f'  PAIR {count}: {name or "REVIEW NAME"} | {start:%Y-%m-%d %H:%M} -> {end:%Y-%m-%d %H:%M} | {zone} | {method}')
            if not name:
                print('    BEFORE:', before[-220:].replace('\n', ' '))
            section_start = label.end()
        print('  COUNT:', count)
    print(f'\nSUMMARY: periods={total} named={named} review_name={total-named} timezone_unverified={uncertain}')
    print('PREVIEW ONLY. Do not register unverified server-time dates.')

if __name__ == '__main__':
    main()
