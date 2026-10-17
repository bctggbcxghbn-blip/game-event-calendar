#!/usr/bin/env python3
"""WuWa V7: read-only audit of event names paired with official article date ranges."""
import argparse
import datetime as dt
import html
import json
import re
import urllib.request
from zoneinfo import ZoneInfo

BASE = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/jp'
JST = ZoneInfo('Asia/Tokyo')
DATE = r'20\d{2}\s*(?:年|[-/])\s*\d{1,2}\s*(?:月|[-/])\s*\d{1,2}\s*日?\s*\d{1,2}\s*[:：時]\s*\d{2}'
RANGE = re.compile(r'(' + DATE + r')\s*(?:~|～|〜|－|–|—|から|至|-)\s*(' + DATE + r')')
LABEL = re.compile(r'(?:✦\s*)?(?:開催期間|イベント期間|実施期間|開放期間|挑戦期間)(?:\s*✦)?\s*[:：]?')
QUOTE = re.compile(r'[「『＜<]([^」』＞>]{3,65})[」』＞>]')


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as res:
        return json.load(res)


def clean(s):
    s = html.unescape(str(s or ''))
    s = re.sub(r'<(?:br|/p|/div|/li|/h[1-6])\b[^>]*>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]*>', ' ', s)
    s = re.sub(r'[ \t\u3000]+', ' ', s)
    s = re.sub(r'\n\s*\n+', '\n', s)
    return s.strip()


def date_jst(s):
    m = re.search(r'(20\d{2})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{2})', s)
    if not m:
        return '?'
    try:
        return dt.datetime(*map(int, m.groups()), tzinfo=JST).strftime('%Y-%m-%d %H:%M')
    except ValueError:
        return '?'


def identify_name(pre):
    """Heuristic name candidate only; human verification required."""
    lines = [x.strip(' ✦・-') for x in pre.splitlines() if x.strip()]
    # Prefer recent short line with a quoted event title, ignoring date/period lines.
    for line in reversed(lines[-12:]):
        if len(line) > 130 or re.search(r'開催期間|20\d{2}年|サーバー時間|報酬|参加条件', line):
            continue
        q = QUOTE.search(line)
        if q and len(line) <= 105:
            return q.group(1).strip(), 'quoted-heading'
    for line in reversed(lines[-8:]):
        if 5 <= len(line) <= 55 and not re.search(r'[。！？]|開催期間|20\d{2}年|サーバー時間|条件|報酬', line):
            return line, 'short-line'
    return '(未確定)', 'unknown'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--article-ids', nargs='+', default=['5570', '5356', '5108'])
    args = ap.parse_args()
    print('WUWA V7 EVENT NAME / PERIOD PAIRING - READ ONLY')
    print('IMPORTANT: Timezone and event names must be reviewed before applying.')
    total = 0
    for aid in args.article_ids:
        obj = fetch('/article/' + aid + '.json')
        title = clean(obj.get('articleTitle', '')).replace('\n', ' ')
        body = clean(obj.get('articleContent', ''))
        print('\nARTICLE:', aid, title)
        print('SOURCE:', 'https://wutheringwaves.kurogames.com/jp/main/news/detail/' + aid)
        found = 0
        for label in LABEL.finditer(body):
            after = body[label.end():label.end()+240]
            match = RANGE.search(after)
            if not match or match.start() > 75:
                continue
            pre = body[max(0, label.start()-650):label.start()]
            name, method = identify_name(pre)
            found += 1
            total += 1
            print('  PAIR', found, '| NAME_CANDIDATE:', name, '| METHOD:', method)
            print('    RANGE:', date_jst(match.group(1)), '->', date_jst(match.group(2)), '(as written; timezone unverified)')
            print('    BEFORE:', re.sub(r'\s+', ' ', pre[-230:])[:230])
            print('    AFTER:', re.sub(r'\s+', ' ', after[:125]))
        print('  PAIRS:', found)
    print('\nTOTAL PAIRS:', total)
    print('NO FILE CHANGES. Do not run --apply; V7 has no apply mode.')

if __name__ == '__main__':
    main()
