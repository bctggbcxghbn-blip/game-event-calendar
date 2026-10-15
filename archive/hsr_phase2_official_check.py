#!/usr/bin/env python3
"""Read-only HSR Phase II official news checker. Never changes events.json."""
import json
import re
from pathlib import Path
from hsr_official_candidates import fetch, as_text, EXPECTED_UID, EXPECTED_CERT, RANGE, candidate

ROOT = Path(__file__).resolve().parent
TITLE = re.compile(r'(?:event\s+warp|warp\s+event)\s*[:：].*phase\s*(?:ii|2)\b', re.I)

def main():
    rows = json.loads((ROOT / 'events.json').read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('events.json must be a list')
    print('MODE: READ ONLY; no changes to events.json')
    print('=== WIKI PHASE II CANDIDATES ===')
    for row in rows:
        if isinstance(row, dict) and row.get('game') == 'hsr' and str(row.get('id', '')).startswith('wiki-hsr-gacha-') and row.get('start') == '2026-10-21':
            print('WIKI:', row.get('name'), '|', row.get('kind'), '|', row.get('start'), '->', row.get('end'), '|', row.get('start_time', '?'), '->', row.get('end_time', '?'))
    articles = {}
    for category in (1, 2, 3):
        try:
            data = fetch('getNewsList', {'gids': 6, 'type': category, 'page_size': 50})
            for entry in data.get('list') or []:
                post = entry.get('post') or {}
                pid, title = str(post.get('post_id') or ''), str(post.get('subject') or '')
                if pid.isdigit() and TITLE.search(title):
                    articles[pid] = title
        except Exception as exc:
            print('WARNING news list:', category, type(exc).__name__, str(exc)[:200])
    print('\nPhase II article candidates:', len(articles))
    found = 0
    for pid, title in articles.items():
        try:
            wrapper = (fetch('getPostFull', {'post_id': pid}).get('post') or {})
            post, author = wrapper.get('post') or {}, wrapper.get('user') or {}
            cert = author.get('certification') or {}
            if not (str(author.get('uid')) == EXPECTED_UID and author.get('nickname') == 'Honkai: Star Rail' and isinstance(cert, dict) and cert.get('desc') == EXPECTED_CERT and TITLE.search(str(post.get('subject') or ''))):
                print('SKIP: unverified publisher/title:', pid)
                continue
            body = as_text(post)
            print('\nOFFICIAL:', post.get('subject'))
            print('URL: https://www.hoyolab.com/article/' + pid)
            for m in RANGE.finditer(body):
                c = candidate(m, body)
                if not c:
                    continue
                print('PERIOD:', c['start'], c['start_label'] or c['start_time'], '->', c['end'], c['end_time'], '|', c['timezone'])
                print('BEFORE:', ' '.join(body[max(0, m.start()-380):m.start()].split())[-380:])
            found += 1
        except Exception as exc:
            print('WARNING article:', pid, type(exc).__name__, str(exc)[:200])
    if not found:
        print('No verified Phase II announcement found in the checked recent-news lists. This does not prove it is unpublished.')
    print('Done; events.json unchanged. Do not auto-apply without banner and timezone verification.')

if __name__ == '__main__':
    main()
