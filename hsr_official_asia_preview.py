#!/usr/bin/env python3
"""Read-only Asia-server/JST preview for single-event HSR announcements.

Asia-server 'server time' is treated as UTC+08:00, only for this preview.
Never edits events.json. Mixed or unspecified timezones require review.
"""
import datetime as dt
import json
import pathlib

from hsr_official_match_preview import (
    MAX_ARTICLES, ROOT, kind_for_title, normalize, TYPES,
)
from hsr_official_candidates import (
    EXPECTED_CERT, EXPECTED_UID, RANGE, as_text, candidate, fetch,
)

UTC8 = dt.timezone(dt.timedelta(hours=8))
JST = dt.timezone(dt.timedelta(hours=9))


def convert(date, clock):
    source = dt.datetime.strptime(f'{date} {clock}', '%Y-%m-%d %H:%M').replace(tzinfo=UTC8)
    return source.astimezone(JST).strftime('%Y-%m-%d %H:%M')


def main():
    rows = json.loads((ROOT / 'events.json').read_text(encoding='utf-8'))
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
                    ids.setdefault(pid, str(post.get('subject') or ''))
        except Exception as exc:
            print(f'WARNING: news category {category}: {exc}')
    print(f'Found {len(ids)} articles; Asia-server JST preview only.')
    count = 0
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
                    and isinstance(cert, dict) and cert.get('desc') == EXPECTED_CERT):
                print(f'SKIP: publisher mismatch {pid}')
                continue
            if kind_for_title(str(post.get('subject') or fallback))[0] != kind:
                continue
            extracted = []
            for m in RANGE.finditer(as_text(post)):
                c = candidate(m, as_text(post))
                if c and c not in extracted:
                    extracted.append(c)
            print(f'\nARTICLE: {post.get("subject") or fallback}')
            print(f'URL: https://www.hoyolab.com/article/{pid}')
            if len(extracted) != 1:
                print(f'  REVIEW: {len(extracted)} date ranges; expected one')
                continue
            c = extracted[0]
            print(f'  SOURCE: {c["start"]} {c["start_label"] or c["start_time"]} -> {c["end"]} {c["end_time"]} [{c["timezone"]}]')
            if c['timezone'] not in ('UTC+8', 'server time (region unknown)'):
                print('  REVIEW: unknown timezone; no conversion')
                continue
            try:
                end_jst = convert(c['end'], c['end_time'])
                start_jst = (f'{c["start"]} アップデート後 (時刻未確定)'
                             if c['start_label'] else convert(c['start'], c['start_time']))
            except (ValueError, TypeError) as exc:
                print(f'  REVIEW: invalid time: {exc}')
                continue
            print(f'  ASIA -> JST: {start_jst} -> {end_jst}')
            if c['timezone'].startswith('server time'):
                print('  ASSUMPTION: server time = Asia server (UTC+8); other regions differ')
            matches = []
            for e in rows:
                if not isinstance(e, dict) or e.get('game') != 'hsr':
                    continue
                names = (e.get('name', ''), e.get('original_name', ''))
                if not any(any(normalize(alias) in normalize(name) for alias in aliases)
                           for name in names):
                    continue
                # Match dates before conversion to avoid unintended date rollover matches.
                if (e.get('start'), e.get('end')) == (c['start'], c['end']):
                    matches.append(e)
            if len(matches) == 1:
                print(f'  MATCH (review required): {matches[0].get("name")} | id={matches[0].get("id")}')
            elif not matches:
                print('  NO MATCH: name and source dates do not match existing HSR event')
            else:
                print(f'  AMBIGUOUS: {len(matches)} matching rows')
            print('  NO WRITE: preview only; mixed timezones within a range are not independently validated')
            count += 1
        except Exception as exc:
            print(f'WARNING: article {pid}: {type(exc).__name__}: {exc}')
    print(f'\nDone: {count} JST previews; events.json unchanged.')


if __name__ == '__main__':
    main()
