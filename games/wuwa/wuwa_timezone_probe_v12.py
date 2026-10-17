#!/usr/bin/env python3
"""WuWa V12: read-only official timezone evidence audit. No timezone assumptions."""
import argparse
import html
import json
import re
import urllib.request

BASE = 'https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/'
TZ = re.compile(r'UTC\s*[+-]\s*\d{1,2}|GMT\s*[+-]\s*\d{1,2}|日本標準時|JST|サーバー時間|server time|server timezone|サーバー時刻|サーバーのタイムゾーン', re.I)
DATE = re.compile(r'20\d{2}年\d{1,2}月\d{1,2}日\d{1,2}[:：]\d{2}|20\d{2}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}')

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 WuWa timezone audit'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)

def flatten(value):
    if isinstance(value, dict):
        return ' '.join(flatten(v) for v in value.values())
    if isinstance(value, list):
        return ' '.join(flatten(v) for v in value)
    return str(value or '')

def clean(raw):
    raw = html.unescape(flatten(raw))
    raw = re.sub(r'<(?:br|/p|/div|/h[1-6])\b[^>]*>', '\n', raw, flags=re.I)
    raw = re.sub(r'<[^>]*>', ' ', raw)
    return re.sub(r'\s+', ' ', raw).strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ids', nargs='+', default=['5570', '5356', '5108', '5547', '5472'])
    parser.add_argument('--max-matches', type=int, default=12)
    args = parser.parse_args()
    print('WUWA V12 OFFICIAL TIMEZONE EVIDENCE / READ ONLY')
    print('Goal: determine whether official JP articles explicitly define サーバー時間 as a UTC offset.')
    print('No inferred conversions. events.json unchanged.')
    evidence = []
    for locale in ('jp', 'en'):
        for aid in args.ids:
            url = f'{BASE}{locale}/article/{aid}.json'
            try:
                data = fetch(url)
                title = clean(data.get('articleTitle', ''))[:110]
                body = clean(data.get('articleContent', ''))
            except Exception as exc:
                print(f'FETCH ERROR: {locale} {aid}: {type(exc).__name__}: {exc}')
                continue
            matches = list(TZ.finditer(body))
            print(f'\nARTICLE: {locale}/{aid} | {title} | TZ MENTIONS: {len(matches)}')
            for m in matches[:args.max_matches]:
                context = body[max(0, m.start()-110):min(len(body), m.end()+125)]
                print('  TERM:', m.group(0), '| CONTEXT:', context)
                if re.search(r'(?:サーバー時間|server time).{0,100}(?:UTC|GMT|JST|日本標準時)|(?:UTC|GMT|JST|日本標準時).{0,100}(?:サーバー時間|server time)', context, re.I):
                    evidence.append((locale, aid, context))
            if len(matches) > args.max_matches:
                print(f'  ... {len(matches)-args.max_matches} additional mentions omitted')
            print('  DATE SAMPLES:', DATE.findall(body)[:5])
    print('\nPOSSIBLE SAME-CONTEXT TIMEZONE EVIDENCE:', len(evidence))
    for locale, aid, snippet in evidence[:12]:
        print('  REVIEW:', locale, aid, snippet)
    print('IMPORTANT: co-occurrence alone does NOT prove server-time offset.')
    print('RESULT: Do not convert サーバー時間 without explicit mapping for the relevant region.')
    print('DONE. No file changes.')

if __name__ == '__main__':
    main()
