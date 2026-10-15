#!/usr/bin/env python3
"""Read-only preview of official HSR warp announcements and existing Wiki warps.

Never changes events.json. Article identity is checked against observed HoYoLAB
publisher metadata; a human should still review character/banner associations.
"""
import json
import re
from pathlib import Path
from hsr_official_candidates import fetch, as_text, EXPECTED_UID, EXPECTED_CERT, RANGE, candidate

ROOT = Path(__file__).resolve().parents[2]
WARP_TITLE = re.compile(r'(?:event\s+warp|warp\s+event)\s*[:：]', re.I)
PHASE = re.compile(r'phase\s*(?:i{1,3}|[12])\b', re.I)
NAME = re.compile(r'["“]([^"”]{2,90})["”]')

def main():
    events_file = ROOT / 'events.json'
    if not events_file.is_file():
        print('WARNING: events.json not found; article-only preview')
        rows = []
    else:
        rows = json.loads(events_file.read_text(encoding='utf-8'))
        if not isinstance(rows, list):
            raise ValueError('events.json must be an array')
    articles = {}
    for category in (1, 2, 3):
        try:
            data = fetch('getNewsList', {'gids': 6, 'type': category, 'page_size': 20})
            for entry in data.get('list') or []:
                post = entry.get('post') or {}
                pid = str(post.get('post_id') or '')
                title = str(post.get('subject') or '')
                if pid.isdigit() and WARP_TITLE.search(title):
                    articles[pid] = title
        except Exception as exc:
            print(f'WARNING: news list {category}: {type(exc).__name__}: {exc}')
    print(f'Found {len(articles)} warp article(s) in recent news lists.')
    count = 0
    for pid, title in list(articles.items())[:12]:
        try:
            wrapper = (fetch('getPostFull', {'post_id': pid}).get('post') or {})
            post, user = wrapper.get('post') or {}, wrapper.get('user') or {}
            cert = user.get('certification') or {}
            if not (str(user.get('uid')) == EXPECTED_UID and
                    user.get('nickname') == 'Honkai: Star Rail' and
                    isinstance(cert, dict) and cert.get('desc') == EXPECTED_CERT):
                print(f'SKIP {pid}: publisher metadata not matched')
                continue
            actual_title = str(post.get('subject') or title)
            if not WARP_TITLE.search(actual_title):
                print(f'SKIP {pid}: article title changed')
                continue
            body = as_text(post)
            print(f'\nARTICLE: {actual_title}')
            print(f'URL: https://www.hoyolab.com/article/{pid}')
            phase = PHASE.search(actual_title)
            print('PHASE:', phase.group(0) if phase else 'not identified')
            matches = list(RANGE.finditer(body))
            print(f'DATE RANGE CANDIDATES: {len(matches)}')
            for m in matches[:8]:
                item = candidate(m, body)
                if not item:
                    continue
                print('  PERIOD:', item['start'], item['start_label'] or item['start_time'],
                      '->', item['end'], item['end_time'], '|', item['timezone'])
                print('  CONTEXT:', item['context'][:180])
            quoted = list(dict.fromkeys(NAME.findall(body)))[:16]
            print('QUOTED NAMES (not verified as banners):', ', '.join(quoted) or 'none')
            article_dates = {c['start'] for m in matches if (c := candidate(m, body))}
            # Wiki imports identify warp rows primarily through kind and id,
            # not through the character/banner name itself.
            possible = [e for e in rows if isinstance(e, dict)
                        and e.get('game') == 'hsr'
                        and str(e.get('start') or '') in article_dates
                        and (str(e.get('id') or '').startswith('wiki-hsr-gacha-')
                             or any(term in str(e.get('kind') or '').casefold()
                                    for term in ('ガチャ', '復刻キャラ', '跳躍', 'warp')))]
            print(f'EXISTING WARP ROWS WITH SAME START DATE: {len(possible)} (date-only, NOT a verified match)')
            for e in possible[:20]:
                print('  WIKI CANDIDATE:', e.get('name'), '| kind=', e.get('kind'),
                      '|', e.get('start'), '->', e.get('end'),
                      '| start=', e.get('start_label') or e.get('start_time') or 'unconfirmed',
                      '| end=', e.get('end_time') or 'unconfirmed', '| id=', e.get('id'))
            if possible and phase and 'phase i' in phase.group(0).casefold() and 'phase ii' not in phase.group(0).casefold():
                print('  NOTE: Phase I candidates identified by date only; banner names and start labels still need review.')
            count += 1
        except Exception as exc:
            print(f'WARNING: article {pid}: {type(exc).__name__}: {exc}')
    print(f'\nDone: {count} official-metadata-matched warp article previews; events.json unchanged.')
    print('Do not auto-apply: each banner name, phase and timezone still require validation.')

if __name__ == '__main__':
    main()
