#!/usr/bin/env python3
"""V26 read-only: dynamically discover official JP gacha articles and preview banners.
No writes, no --apply. Depends on wuwa_official_discovery_v24.py.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wuwa_official_discovery_v24 as discovery

JST = ZoneInfo('Asia/Tokyo')
UTC8 = dt.timezone(dt.timedelta(hours=8))
DATE = r'20\d{2}年\s*\d{1,2}月\s*\d{1,2}日\s*\d{1,2}[:：時]\d{2}'
STAMP = re.compile(DATE)
RANGE = re.compile(r'('+DATE+r')\s*[~～〜－–—-]\s*('+DATE+r')')
VERSION = re.compile(r'Ver\.?\s*(\d+\.\d+)', re.I)
SECTION = re.compile(r'(共鳴者集音|武器集音)\s*[（(](?:イベント|追憶)[）)]\s*(?:[—–\-]+\s*)?[「『]([^」』]+)[」』]')
FEATURE = {'共鳴者集音': re.compile(r'星\s*5\s*共鳴者\s*[「『]([^」』]+)[」』]'),
           '武器集音': re.compile(r'星\s*5\s*武器\s*[「『]([^」』]+)[」』]')}
PERIOD = re.compile(r'✦\s*開催期間\s*✦?\s*[:：]?')
MAINT = re.compile(r'メンテナンス(?:日時|時間)\s*[：:]\s*('+DATE+r')\s*[~～〜－–—-]\s*('+DATE+r')\s*[（(]\s*UTC\s*\+\s*8\s*[）)]', re.I)

def dateparse(value, tz):
    digits = list(map(int, re.findall(r'\d+', value)))
    if len(digits) != 5:
        raise ValueError('bad timestamp')
    return dt.datetime(*digits, tzinfo=tz).astimezone(JST)

def discover(days):
    seen = {}
    for index in ('ArticleMenu.json', 'MainMenu.json'):
        rows = discovery.rows_from(discovery.fetch(index))
        print('INDEX:', index, 'ROWS:', len(rows))
        for row in rows:
            if not isinstance(row, dict):
                continue
            aid = str(row.get('articleId') or row.get('id') or '')
            title = discovery.clean(row.get('articleTitle') or row.get('title'))
            published = str(row.get('startTime') or row.get('publishTime') or row.get('createTime') or '')
            if aid.isdigit() and title and (aid not in seen or published > seen[aid]['published']):
                seen[aid] = dict(id=aid, title=title, published=published)
    cutoff = dt.date.today() - dt.timedelta(days=max(0, days))
    relevant = []
    for item in seen.values():
        try:
            d = dt.date.fromisoformat(item['published'][:10])
        except ValueError:
            print('SKIP_UNDATED:', item['id']) if ('集音' in item['title']) else None
            continue
        if d >= cutoff:
            relevant.append(item)
    relevant.sort(key=lambda x: (x['published'], int(x['id'])), reverse=True)
    return relevant

def body(aid):
    data = discovery.fetch('article/' + aid + '.json')
    if not isinstance(data, dict):
        raise ValueError('unexpected article JSON')
    return discovery.clean(data.get('articleContent'))

def maintenance_map(items):
    out = {}
    for item in items:
        if 'メンテナンス' not in item['title']:
            continue
        version = VERSION.search(item['title'])
        if not version:
            continue
        try:
            m = MAINT.search(body(item['id']))
            if m:
                start = dateparse(m.group(2), UTC8)
                out[version.group(1)] = (start, item['id'])
                print('MAINTENANCE_START:', version.group(1), start.isoformat(timespec='minutes'), 'ARTICLE:', item['id'])
            else:
                print('MAINTENANCE_UNPARSED:', item['id'])
        except Exception as e:
            print('MAINTENANCE_ERROR:', item['id'], type(e).__name__, str(e)[:100])
    return out

def parse_banners(item, content, maintenance):
    headings = list(SECTION.finditer(content))
    if not headings:
        return [], 'NO_BANNER_SECTIONS'
    results = []
    for i, heading in enumerate(headings):
        category, banner = heading.group(1), heading.group(2)
        chunk = content[heading.end():headings[i+1].start() if i+1 < len(headings) else len(content)]
        feat = FEATURE[category].search(chunk[:500])
        period = PERIOD.search(chunk)
        record = {'type': 'CHARACTER' if category == '共鳴者集音' else 'WEAPON',
                  'banner': banner, 'featured': feat.group(1) if feat else '?', 'status': 'HOLD'}
        if not period:
            record['reason'] = 'NO_PERIOD'
            results.append(record)
            continue
        ptext = chunk[period.end():period.end()+170]
        tz = re.search(r'[（(]\s*(?:日本標準時|JST)\s*[）)]', ptext)
        if not tz:
            record['reason'] = 'NO_EXPLICIT_JST'
            results.append(record)
            continue
        prefix = ptext[:tz.start()]
        pair = RANGE.search(prefix)
        if pair:
            try:
                start, end = dateparse(pair.group(1), JST), dateparse(pair.group(2), JST)
                record['status'] = 'PARSED'
                record['basis'] = 'EXPLICIT_JST'
            except ValueError:
                record['reason'] = 'INVALID_DATE'
                results.append(record)
                continue
        elif re.search(r'Ver\.?\s*\d+\.\d+\s*の?アップデート後', prefix, re.I):
            end_match = STAMP.search(prefix)
            ver = VERSION.search(prefix) or VERSION.search(item['title'])
            if not end_match or not ver or ver.group(1) not in maintenance:
                record['reason'] = 'MISSING_END_OR_MAINTENANCE'
                results.append(record)
                continue
            try:
                start = maintenance[ver.group(1)][0]
                end = dateparse(end_match.group(), JST)
                record['status'] = 'PARSED_PLANNED'
                record['basis'] = 'MAINTENANCE_PLANNED_END_AND_EXPLICIT_JST'
            except ValueError:
                record['reason'] = 'INVALID_DATE'
                results.append(record)
                continue
        else:
            record['reason'] = 'UNSUPPORTED_PERIOD_FORMAT'
            results.append(record)
            continue
        if start >= end:
            record['status'] = 'HOLD'
            record['reason'] = 'START_NOT_BEFORE_END'
        else:
            record['start_jst'] = start.isoformat(timespec='minutes')
            record['end_jst'] = end.isoformat(timespec='minutes')
        results.append(record)
    return results, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days-back', type=int, default=120)
    ap.add_argument('--limit', type=int, default=30)
    ap.add_argument('--events', default='events.json')
    args = ap.parse_args()
    print('WUWA V26 DYNAMIC OFFICIAL GACHA / READ ONLY')
    print('No apply mode. Never modifies events.json. JST only; planned maintenance start labeled.')
    items = discover(args.days_back)
    print('RECENT_ARTICLES:', len(items))
    maintenance = maintenance_map(items)
    gachas = [x for x in items if re.search(r'集音|ピックアップ', x['title'])]
    print('GACHA_ARTICLES:', len(gachas), 'INSPECTING:', min(len(gachas), max(0, args.limit)))
    try:
        existing = json.loads(Path(args.events).read_text(encoding='utf-8'))
        if not isinstance(existing, list):
            raise ValueError('events.json is not an array')
        print('EXISTING_EVENTS:', len(existing))
    except Exception as exc:
        print('EXISTING_EVENTS_UNAVAILABLE:', type(exc).__name__, str(exc)[:100])
        existing = []
    counts = {'PARSED': 0, 'PARSED_PLANNED': 0, 'HOLD': 0}
    for item in gachas[:max(0, args.limit)]:
        print('\nARTICLE:', item['id'], '|', item['title'])
        print('URL:', discovery.SITE + item['id'])
        try:
            content = body(item['id'])
            if not content:
                print('BODY_EMPTY (possibly image-based)')
                continue
            records, error = parse_banners(item, content, maintenance)
            if error:
                print('HOLD:', error)
            for record in records:
                status = record['status']
                counts[status] += 1
                name = record['banner']
                featured = record['featured']
                if status.startswith('PARSED'):
                    start, end = record['start_jst'], record['end_jst']
                    # Advisory duplicate check only: names differ across earlier importer versions.
                    candidates = [x for x in existing if x.get('game') == 'wuwa' and x.get('kind') == 'gacha'
                                  and x.get('start') == start[:10] and x.get('end') == end[:10]
                                  and (name in str(x.get('name', '')) or featured in str(x.get('name', '')))]
                    print(status, record['type'], name, '|', featured, '|', start, '->', end,
                          '|', record['basis'], '|', 'POSSIBLE_EXISTING='+str(len(candidates)))
                else:
                    print('HOLD', record['type'], name, '|', featured, '|', record.get('reason', 'UNKNOWN'))
        except Exception as e:
            print('ARTICLE_ERROR:', type(e).__name__, str(e)[:160])
    print('\nSUMMARY:', ' '.join(k+'='+str(v) for k, v in counts.items()), 'READ_ONLY=true')
    print('Dates are candidates for review, NOT imported. Duplicate checks are advisory.')

if __name__ == '__main__':
    main()
