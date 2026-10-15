#!/usr/bin/env python3
"""Read-only verification report for HSR Version 4.6 Phase I warp banners.

Prints official article passages and existing Wiki rows side-by-side.
Does not infer banner identity from dates and NEVER edits events.json.
"""
import json
import re
from pathlib import Path
from hsr_official_candidates import fetch, as_text, EXPECTED_UID, EXPECTED_CERT, RANGE, candidate

ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ID = '46851682'
START = '2026-09-28'
END = '2026-10-21'


def compact(text):
    return ' '.join(text.split())


def main():
    rows = json.loads((ROOT / 'events.json').read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('events.json must be a list')
    wrapper = fetch('getPostFull', {'post_id': ARTICLE_ID}).get('post') or {}
    post, author = wrapper.get('post') or {}, wrapper.get('user') or {}
    cert = author.get('certification') or {}
    if not (str(author.get('uid')) == EXPECTED_UID
            and author.get('nickname') == 'Honkai: Star Rail'
            and isinstance(cert, dict) and cert.get('desc') == EXPECTED_CERT
            and 'event warp: phase i' in str(post.get('subject') or '').casefold()):
        print('STOP: article author/title metadata did not match expected values.')
        return
    body = as_text(post)
    print('ARTICLE:', post.get('subject'))
    print('SOURCE: https://www.hoyolab.com/article/' + ARTICLE_ID)
    print('MODE: READ ONLY. All associations require review.\n')
    print('=== PERIODS IN ARTICLE (WITH SURROUNDING CONTEXT) ===')
    n = 0
    for match in RANGE.finditer(body):
        item = candidate(match, body)
        if not item:
            continue
        n += 1
        print(f'\nPERIOD #{n}: {item["start"]} {item["start_label"] or item["start_time"]} '
              f'-> {item["end"]} {item["end_time"]} [{item["timezone"]}]')
        print('BEFORE:', compact(body[max(0, match.start()-400):match.start()])[-400:])
        print('AFTER:', compact(body[match.end():match.end()+180])[:180])
        if item['start'] == START and item['end'] == END:
            print('DATE MATCH: Wiki Phase I end date (not proof of banner identity)')
    print('\n=== EXISTING WIKI WARP ROWS ===')
    existing = [r for r in rows if isinstance(r, dict) and r.get('game') == 'hsr'
                and str(r.get('id', '')).startswith('wiki-hsr-gacha-')
                and r.get('start') == START and r.get('end') == END]
    for row in existing:
        print('WIKI:', row.get('name'), '|', row.get('kind'), '|', row.get('id'),
              '| start:', row.get('start_label') or row.get('start_time') or 'unconfirmed',
              '| end:', row.get('end_time') or 'unconfirmed')
    print(f'\nSUMMARY: {n} article period mentions; {len(existing)} Wiki rows; no writes.')
    print('NEXT: Confirm each Japanese banner name against its English banner name and exact period.')


if __name__ == '__main__':
    main()
