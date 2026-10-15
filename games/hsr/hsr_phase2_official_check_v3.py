#!/usr/bin/env python3
"""Read-only official HSR 4.6 Phase II checker with GitHub Actions annotations."""
import json
import os
import re
from pathlib import Path
from hsr_official_candidates import fetch, as_text, EXPECTED_UID, EXPECTED_CERT, RANGE, candidate

ROOT = Path(__file__).resolve().parents[2]
TARGET = re.compile(r'\bversion\s*4[.]6\b.*\bevent\s+warp\s*[:：]\s*phase\s*(?:ii|2)\b', re.I)

def annotate(level, message):
    # GitHub workflow command: escape payload to avoid malformed annotations.
    safe = str(message).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'::{level}::{safe}')

def main():
    rows = json.loads((ROOT / 'events.json').read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('events.json must contain an array')
    print('MODE: READ ONLY; events.json unchanged')
    print('=== CURRENT WIKI PHASE II ROWS ===')
    for e in rows:
        if isinstance(e, dict) and e.get('game') == 'hsr' and str(e.get('id', '')).startswith('wiki-hsr-gacha-') and e.get('start') == '2026-10-21':
            print('WIKI:', e.get('name'), '|', e.get('start'), '->', e.get('end'), '|', e.get('start_time', '?'), '->', e.get('end_time', '?'))

    found, errors, verified_urls = {}, 0, []
    for category in (1, 2, 3):
        try:
            data = fetch('getNewsList', {'gids': 6, 'type': category, 'page_size': 50})
            for entry in data.get('list') or []:
                post = entry.get('post') or {}
                pid = str(post.get('post_id') or '')
                if pid.isdigit() and TARGET.search(str(post.get('subject') or '')):
                    found[pid] = post.get('subject')
        except Exception as exc:
            errors += 1
            print('WARNING: news list', category, type(exc).__name__, str(exc)[:180])

    for pid, title in found.items():
        try:
            wrapper = fetch('getPostFull', {'post_id': pid}).get('post') or {}
            post, author = wrapper.get('post') or {}, wrapper.get('user') or {}
            cert = author.get('certification') or {}
            if not (str(author.get('uid')) == EXPECTED_UID and author.get('nickname') == 'Honkai: Star Rail' and isinstance(cert, dict) and cert.get('desc') == EXPECTED_CERT and TARGET.search(str(post.get('subject') or ''))):
                print('SKIP: publisher/title not verified:', pid)
                continue
            url = 'https://www.hoyolab.com/article/' + pid
            verified_urls.append(url)
            print('\nOFFICIAL:', post.get('subject'))
            print('URL:', url)
            body = as_text(post)
            for m in RANGE.finditer(body):
                c = candidate(m, body)
                if c:
                    print('PERIOD:', c['start'], c['start_label'] or c['start_time'], '->', c['end'], c['end_time'], '|', c['timezone'])
                    print('BEFORE:', ' '.join(body[max(0, m.start()-350):m.start()].split())[-350:])
        except Exception as exc:
            errors += 1
            print('WARNING: article', pid, type(exc).__name__, str(exc)[:180])

    summary = ['## HSR Version 4.6 Phase II official warp check', '', '**Read-only:** events.json was not modified.', '']
    if verified_urls:
        annotate('notice', 'HSR Ver.4.6 Phase II official warp article found! Review dates and banner names before updating.')
        print('\n*** OFFICIAL PHASE II ARTICLE FOUND — MANUAL REVIEW REQUIRED ***')
        summary += ['**FOUND — manual review required.**', ''] + [f'- {url}' for url in verified_urls]
    else:
        print('\nVersion 4.6 Phase II: NOT FOUND in checked official news lists.')
        print('This does not prove the notice has not been published.')
        summary += ['**NOT FOUND** in checked official news lists. This does not prove non-publication.']
    if errors:
        annotate('warning', f'HSR Phase II check had {errors} failed request(s); results may be incomplete.')
        summary += ['', f'**Warning:** {errors} request(s) failed; search may be incomplete.']
    print('Keeping existing Wiki data unchanged.')
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(summary) + '\n')

if __name__ == '__main__':
    main()
