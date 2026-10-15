#!/usr/bin/env python3
"""Read-only preview: match single-event HSR official news to existing events.

Never writes events.json. Server-time clocks are deliberately not converted.
"""
import json
import pathlib
import re

from hsr_official_candidates import (
    EXPECTED_CERT, EXPECTED_UID, RANGE, as_text, candidate, fetch,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAX_ARTICLES = 60
# Single-event announcements only. Broad patch notes and multi-warp posts are excluded.
TYPES = {
    'planar fissure': ('次元界分裂', 'planar fissure'),
    'realm of the strange': ('遺物', 'realm of the strange', '異器'),
}


def normalize(value):
    return re.sub(r'[\W_]+', '', str(value).casefold())


def kind_for_title(title):
    lowered = title.casefold()
    for prefix, aliases in TYPES.items():
        if lowered.startswith(prefix + ' event:'):
            return prefix, aliases
    return None, ()


def main():
    path = ROOT / 'events.json'
    rows = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('events.json must be a list')
    ids = {}
    for category in (1, 2, 3):
        try:
            data = fetch('getNewsList', {'gids': 6, 'type': category, 'page_size': 20})
            for entry in data.get('list') or []:
                post = entry.get('post') or {}
                pid = str(post.get('post_id') or '')
                if pid.isdigit():
                    ids.setdefault(pid, post.get('subject') or '')
        except Exception as exc:
            print(f'WARNING: news category {category}: {exc}')
    print(f'Found {len(ids)} articles. Checking up to {MAX_ARTICLES}.')
    previews = 0
    for pid, fallback in list(ids.items())[:MAX_ARTICLES]:
        kind, aliases = kind_for_title(fallback)
        if not kind:
            continue
        try:
            data = fetch('getPostFull', {'post_id': pid})
            wrapper = data.get('post') or {}
            post = wrapper.get('post') or {}
            user = wrapper.get('user') or {}
            cert = user.get('certification') or {}
            if not (str(user.get('uid')) == EXPECTED_UID
                    and user.get('nickname') == 'Honkai: Star Rail'
                    and isinstance(cert, dict)
                    and cert.get('desc') == EXPECTED_CERT):
                print(f'SKIP: publisher mismatch {pid}')
                continue
            title = str(post.get('subject') or fallback)
            if kind_for_title(title)[0] != kind:
                continue
            body = as_text(post)
            extracted = []
            for match in RANGE.finditer(body):
                item = candidate(match, body)
                if item and item not in extracted:
                    extracted.append(item)
            print(f'\nARTICLE: {title}\nURL: https://www.hoyolab.com/article/{pid}')
            if len(extracted) != 1:
                print(f'  REVIEW ONLY: {len(extracted)} periods; require exactly one')
                continue
            c = extracted[0]
            print(f'  PERIOD: {c["start"]} {c["start_label"] or c["start_time"]} -> {c["end"]} {c["end_time"]} [{c["timezone"]}]')
            # Require matching name AND matching dates. Never match by date alone.
            matches = []
            for event in rows:
                if not isinstance(event, dict) or event.get('game') != 'hsr':
                    continue
                names = (event.get('name', ''), event.get('original_name', ''))
                if not any(any(normalize(alias) in normalize(name) for alias in aliases)
                           for name in names):
                    continue
                if (event.get('start'), event.get('end')) == (c['start'], c['end']):
                    matches.append(event)
            if len(matches) == 1:
                print(f'  MATCH (review required): {matches[0].get("name")} | id={matches[0].get("id")}')
                print('  NO WRITE: server region/timezone and title matching require review')
            elif not matches:
                print('  NO MATCH: no existing HSR event with matching name and dates')
            else:
                print(f'  AMBIGUOUS: {len(matches)} existing events match; skipped')
            previews += 1
        except Exception as exc:
            print(f'WARNING: article {pid}: {type(exc).__name__}: {exc}')
    print(f'\nDone: {previews} single-event previews; events.json unchanged.')


if __name__ == '__main__':
    main()
