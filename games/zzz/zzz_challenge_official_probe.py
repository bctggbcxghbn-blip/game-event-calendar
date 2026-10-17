#!/usr/bin/env python3
"""Find ZZZ challenge mentions in official HoYoLAB news (read-only diagnostic).

This script does NOT infer dates or write confirmed JSON/events.json.
"""
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'games' / 'hsr'))
from hsr_maintenance_detail_probe import DETAIL, LIST, get_json
from hsr_maintenance_time_preview import content_text

CHALLENGE = re.compile(r'shiyu\s*defen[sc]e|critical\s*node|deadly\s*assault|式輿防衛戦|危局強襲戦|式舆防卫战|危局强袭战', re.I)
DATE = re.compile(r'20\d{2}[/.-]\d{1,2}[/.-]\d{1,2}(?:\s+\d{1,2}:\d{2})?|(?:UTC\s*[+-]\s*8)|\b(?:reset|refresh|rotation|更新|開催期間)\b', re.I)


def excerpt(text, match, before=100, after=180):
    return ' '.join(text[max(0, match.start()-before):min(len(text), match.end()+after)].split())[:330]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=50, help='Articles per news type (1..50)')
    p.add_argument('--max-detail', type=int, default=90, help='Max full articles to inspect')
    args = p.parse_args()
    if not 1 <= args.limit <= 50 or not 1 <= args.max_detail <= 150:
        p.error('--limit must be 1..50; --max-detail must be 1..150')

    seen = set()
    articles = []
    failures = 0
    for typ in (1, 2, 3):
        try:
            data = get_json(LIST + '?' + urlencode({'gids': 8, 'type': typ, 'page_size': args.limit}))
            items = data.get('list', [])
            print(f'NEWS TYPE {typ}: {len(items)} articles')
        except Exception as exc:
            print(f'WARNING: news type {typ}: {exc}')
            failures += 1
            continue
        for item in items:
            post = item.get('post', item) if isinstance(item, dict) else {}
            if not isinstance(post, dict):
                continue
            pid = str(post.get('post_id') or post.get('id') or '')
            if not pid.isdigit() or pid in seen:
                continue
            seen.add(pid)
            title = str(post.get('subject') or post.get('title') or '')
            articles.append((pid, title))

    print(f'UNIQUE ARTICLES: {len(articles)}; scanning up to {args.max_detail} full articles')
    matches = 0
    for pid, title in articles[:args.max_detail]:
        try:
            body = content_text(get_json(DETAIL + '?' + urlencode({'post_id': pid})))
        except Exception as exc:
            print(f'WARNING DETAIL {pid}: {type(exc).__name__}: {exc}')
            failures += 1
            continue
        hits = list(CHALLENGE.finditer(title + '\n' + body))
        if not hits:
            continue
        matches += 1
        print(f'\nMATCH: {title}\nURL: https://www.hoyolab.com/article/{pid}')
        for m in hits[:3]:
            print('CHALLENGE CONTEXT:', excerpt(title + '\n' + body, m))
        for m in list(DATE.finditer(body))[:5]:
            print('DATE/RESET CONTEXT:', excerpt(body, m))
        if not DATE.search(body):
            print('NO DATE/RESET CONTEXT found')
    print(f'\nMATCHED ARTICLES: {matches}; REQUEST ERRORS: {failures}')
    print('PREVIEW ONLY. No official dates verified automatically; no files modified.')


if __name__ == '__main__':
    main()
