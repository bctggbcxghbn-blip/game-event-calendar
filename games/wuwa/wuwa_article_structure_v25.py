#!/usr/bin/env python3
"""V25: inspect discovered official article body structures, read-only."""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wuwa_official_discovery_v24 as discovery

BASE = discovery.BASE
SITE = discovery.SITE
TIME = re.compile(r'20\d{2}年\d{1,2}月\d{1,2}日\s*\d{1,2}[:：時]\d{2}')
LABELS = re.compile(r'開催期間|集音期間|メンテナンス(?:日時|時間)|サーバー時間|日本標準時|UTC\s*\+\s*8|アップデート後|終了しました')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=12)
    ap.add_argument('--days-back', type=int, default=120)
    args = ap.parse_args()
    print('WUWA V25 OFFICIAL ARTICLE BODY STRUCTURE / READ ONLY')
    print('No apply mode; events.json will not be changed.')
    seen = {}
    for index in ('ArticleMenu.json', 'MainMenu.json'):
        rows = discovery.rows_from(discovery.fetch(index))
        print('INDEX:', index, 'ROWS:', len(rows))
        for row in rows:
            if not isinstance(row, dict):
                continue
            aid = str(row.get('articleId') or row.get('id') or '')
            title = discovery.clean(row.get('articleTitle') or row.get('title'))
            if not aid.isdigit() or not title:
                continue
            published = str(row.get('startTime') or row.get('publishTime') or row.get('createTime') or '')
            if aid not in seen or published > seen[aid]['published']:
                seen[aid] = dict(id=aid, title=title, published=published)
    cutoff = dt.date.today() - dt.timedelta(days=max(0, args.days_back))
    matched = []
    for item in seen.values():
        categories = [name for name, rule in discovery.RULES if rule.search(item['title'])]
        if not categories:
            continue
        try:
            pubdate = dt.date.fromisoformat(item['published'][:10])
        except ValueError:
            pubdate = None
        if pubdate and pubdate < cutoff:
            continue
        item['categories'] = categories
        matched.append(item)
    matched.sort(key=lambda x: (x['published'], int(x['id'])), reverse=True)
    selected = matched[:max(0, min(args.limit, 40))]
    print('DISCOVERED:', len(matched), 'INSPECTING:', len(selected))
    ok = 0
    for item in selected:
        aid = item['id']
        print('\nARTICLE:', aid, '|', '+'.join(item['categories']), '|', item['title'][:110])
        print('URL:', SITE + aid)
        try:
            raw = discovery.fetch('article/' + aid + '.json')
            if not isinstance(raw, dict):
                print('BODY_ERROR: unexpected JSON root', type(raw).__name__)
                continue
            body = discovery.clean(raw.get('articleContent', ''))
            print('BODY:', 'chars='+str(len(body)), 'keys='+','.join(sorted(raw.keys())[:14]))
            if not body:
                print('BODY_EMPTY')
                continue
            ok += 1
            markers = list(LABELS.finditer(body))
            dates = TIME.findall(body)
            print('DATE_TOKENS:', len(dates), 'EXAMPLES:', ' | '.join(dates[:5]))
            print('MARKERS:', len(markers))
            for m in markers[:7]:
                start = max(0, m.start()-85)
                end = min(len(body), m.end()+145)
                print('CONTEXT:', body[start:end].replace('\n', ' ')[:250])
            if not markers:
                print('BODY_START:', body[:240])
        except Exception as exc:
            print('FETCH_ERROR:', type(exc).__name__, str(exc)[:180])
    print('\nSUMMARY: inspected='+str(len(selected)), 'body_ok='+str(ok), 'read_only=true')
    if not selected or ok == 0:
        raise SystemExit('No usable article bodies; inspect CDN access and structure')

if __name__ == '__main__':
    main()
