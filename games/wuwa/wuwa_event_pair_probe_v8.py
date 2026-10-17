#!/usr/bin/env python3
"""WuWa V8: safe read-only heading/date pairing; no calendar modifications."""
import argparse
import datetime as dt
import html
import json
import re
import urllib.request

BASE = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/jp'
DATE = r'20\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*\d{1,2}\s*[:：時]\s*\d{2}'
RANGE = re.compile(r'(' + DATE + r')\s*(?:~|～|〜|－|–|—|から|至|-)\s*(' + DATE + r')')
LABEL = re.compile(r'(?:✦\s*)?(?:開催期間|イベント期間|実施期間|開放期間|挑戦期間)(?:\s*✦)?\s*[:：]?')
HEADING = re.compile(r'(?:^|\n)\s*([^\n]{0,45}?(?:イベント|ログインボーナス|ログイン特典|特別調査|戦闘|チャレンジ|【H5ウェブイベント】|【WEBイベント】)[^\n]{0,25}?)?[「『]([^」』\n]{2,70})[」』]', re.M)


def fetch(aid):
    req = urllib.request.Request(BASE + '/article/' + str(aid) + '.json', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def clean(s):
    s = html.unescape(str(s or ''))
    s = re.sub(r'<(?:br|/p|/div|/li|/h[1-6])\b[^>]*>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]*>', ' ', s)
    s = re.sub(r'[ \t\u3000]+', ' ', s)
    return re.sub(r'\n\s*\n+', '\n', s).strip()


def date_parts(s):
    m = re.search(r'(20\d{2})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{2})', s)
    if not m:
        return None
    try:
        return dt.datetime(*map(int, m.groups()))
    except ValueError:
        return None


def heading_before(body, label_start, prev_end):
    # Never search before the preceding period: that is how V7 chose unrelated titles.
    segment = body[prev_end:label_start]
    matches = list(HEADING.finditer(segment))
    if not matches:
        return None
    # Prefer a heading near the beginning of the current event section, not quoted prose.
    for match in matches:
        if len(segment[:match.start()].strip()) < 120:
            return match.group(2).strip()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--article-ids', nargs='+', default=['5570', '5356', '5108'])
    args = ap.parse_args()
    print('WUWA V8 HEADING / PERIOD AUDIT - READ ONLY')
    print('Server time is NOT assumed to be JST. UTC+8 is converted to JST for comparison.')
    total = 0
    for aid in args.article_ids:
        article = fetch(aid)
        body = clean(article.get('articleContent', ''))
        print('\nARTICLE:', aid, clean(article.get('articleTitle', '')).replace('\n', ' '))
        labels = list(LABEL.finditer(body))
        prev_end = 0
        count = 0
        for i, label in enumerate(labels):
            next_label_start = labels[i + 1].start() if i + 1 < len(labels) else len(body)
            period_section = body[label.end():next_label_start]
            name = heading_before(body, label.start(), prev_end)
            match = RANGE.search(period_section)
            # Do not borrow a date from a later event or a different paragraph.
            if match and match.start() <= 45 and name:
                start, end = date_parts(match.group(1)), date_parts(match.group(2))
                suffix = period_section[match.end():match.end()+35]
                zone = 'UTC+8' if 'UTC+8' in suffix else ('サーバー時間' if 'サーバー時間' in suffix else '不明')
                if start and end and end >= start:
                    if zone == 'UTC+8':
                        start += dt.timedelta(hours=1)
                        end += dt.timedelta(hours=1)
                        zone_note = 'JST (converted from UTC+8)'
                    else:
                        zone_note = zone + ' (NOT converted)'
                    count += 1
                    total += 1
                    print('  PAIR:', name)
                    print('    PERIOD:', start.strftime('%Y-%m-%d %H:%M'), '->', end.strftime('%Y-%m-%d %H:%M'), '|', zone_note)
            elif name and ('アップデート後' in period_section[:65] or '常時開放' in period_section[:65]):
                print('  SKIP non-explicit period:', name, '|', period_section[:75].replace('\n', ' '))
            prev_end = label.end() + (match.end() if match else 0)
        print('  COUNT:', count)
    print('\nTOTAL:', total, '| NO FILE CHANGES')

if __name__ == '__main__':
    main()
