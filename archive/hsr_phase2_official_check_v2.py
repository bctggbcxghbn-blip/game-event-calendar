#!/usr/bin/env python3
"""Read-only checker for the official HSR Version 4.6 Phase II warp notice."""
import json
import re
from pathlib import Path
from hsr_official_candidates import fetch, as_text, EXPECTED_UID, EXPECTED_CERT, RANGE, candidate

ROOT = Path(__file__).resolve().parent
TARGET = re.compile(r'\bversion\s*4[.]6\b.*\bevent\s+warp\s*[:：]\s*phase\s*(?:ii|2)\b', re.I)

def main():
    rows = json.loads((ROOT / 'events.json').read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('events.json must contain an array')
    print('MODE: READ ONLY; events.json unchanged')
    print('=== CURRENT WIKI PHASE II ROWS ===')
    for e in rows:
        if isinstance(e, dict) and e.get('game') == 'hsr' and str(e.get('id', '')).startswith('wiki-hsr-gacha-') and e.get('start') == '2026-10-21':
            print('WIKI:', e.get('name'), '|', e.get('start'), '->', e.get('end'), '|', e.get('start_time', '?'), '->', e.get('end_time', '?'))
    found = {}
    errors = 0
    for category in (1, 2, 3):
        try:
            data = fetch('getNewsList', {'gids': 6, 'type': category, 'page_size': 50})
            for entry in data.get('list') or []:
                post = entry.get('post') or {}
                pid = str(post.get('post_id') or '')
                title = str(post.get('subject') or '')
                if pid.isdigit() and TARGET.search(title):
                    found[pid] = title
        except Exception as exc:
            errors += 1
            print('WARNING: news list', category, type(exc).__name__, str(exc)[:180])
    verified = 0
    for pid, title in found.items():
        try:
            wrapper = fetch('getPostFull', {'post_id': pid}).get('post') or {}
            post, author = wrapper.get('post') or {}, wrapper.get('user') or {}
            cert = author.get('certification') or {}
            if not (str(author.get('uid')) == EXPECTED_UID and author.get('nickname') == 'Honkai: Star Rail' and isinstance(cert, dict) and cert.get('desc') == EXPECTED_CERT and TARGET.search(str(post.get('subject') or ''))):
                print('SKIP: publisher/title not verified:', pid)
                continue
            verified += 1
            body = as_text(post)
            print('\nOFFICIAL:', post.get('subject'))
            print('URL: https://www.hoyolab.com/article/' + pid)
            for m in RANGE.finditer(body):
                c = candidate(m, body)
                if c:
                    print('PERIOD:', c['start'], c['start_label'] or c['start_time'], '->', c['end'], c['end_time'], '|', c['timezone'])
                    print('BEFORE:', ' '.join(body[max(0, m.start()-350):m.start()].split())[-350:])
        except Exception as exc:
            errors += 1
            print('WARNING: article', pid, type(exc).__name__, str(exc)[:180])
    if not verified:
        print('\nVersion 4.6 Phase II: NOT FOUND in checked official news lists.')
        print('This does not prove the notice has not been published.')
    print('Keeping existing Wiki data unchanged.')
    if errors:
        print('WARNING:', errors, 'request(s) failed; search may be incomplete.')

if __name__ == '__main__':
    main()
