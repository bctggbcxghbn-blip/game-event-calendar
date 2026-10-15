#!/usr/bin/env python3
"""Conservative HSR Asia-server JST updater: existing Planar Fissure rows only.

Run after wiki importers and before reviewed official overrides. No new events.
Other event types and ambiguous articles are intentionally skipped.
"""
import datetime as dt
import json
import os
import pathlib
import re
import tempfile

from hsr_official_candidates import EXPECTED_UID, EXPECTED_CERT, fetch, as_text
from hsr_official_match_preview import ROOT, normalize

EVENTS = ROOT / 'events.json'
TZ_ASIA = dt.timezone(dt.timedelta(hours=8))
TZ_JST = dt.timezone(dt.timedelta(hours=9))
# Only a single, explicitly labeled event period; no arbitrary dates in patch notes.
PERIOD = re.compile(
    r'Event\s+Period\s*[:：]?\s*'
    r'(?P<start>20\d{2}[/-]\d{1,2}[/-]\d{1,2})\s+'
    r'(?P<startclock>\d{1,2}:\d{2})\s*'
    r'(?:\(server\s+time\)\s*)?'
    r'[-–—]\s*'
    r'(?P<end>20\d{2}[/-]\d{1,2}[/-]\d{1,2})\s+'
    r'(?P<endclock>\d{1,2}:\d{2})\s*'
    r'\(server\s+time\)', re.I)


def jst(date, clock):
    source = dt.datetime.strptime(date.replace('/', '-') + ' ' + clock, '%Y-%m-%d %H:%M')
    return source.replace(tzinfo=TZ_ASIA).astimezone(TZ_JST).strftime('%Y-%m-%d %H:%M').split()


def main():
    rows = json.loads(EVENTS.read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('events.json must be a list')
    articles = {}
    for category in (1, 2, 3):
        try:
            result = fetch('getNewsList', {'gids': 6, 'type': category, 'page_size': 20})
            for entry in result.get('list') or []:
                post = entry.get('post') or {}
                pid = str(post.get('post_id') or '')
                if pid.isdigit() and str(post.get('subject') or '').casefold().startswith('planar fissure event:'):
                    articles[pid] = post.get('subject')
        except Exception as exc:
            print(f'WARNING: news list category {category}: {exc}')
    pending = {}
    for pid, title in articles.items():
        try:
            result = fetch('getPostFull', {'post_id': pid})
            wrapper = result.get('post') or {}
            post = wrapper.get('post') or {}
            author = wrapper.get('user') or {}
            cert = author.get('certification') or {}
            if not (str(author.get('uid')) == EXPECTED_UID and author.get('nickname') == 'Honkai: Star Rail'
                    and isinstance(cert, dict) and cert.get('desc') == EXPECTED_CERT):
                print(f'SKIP {pid}: publisher mismatch')
                continue
            if not str(post.get('subject') or '').casefold().startswith('planar fissure event:'):
                continue
            body = as_text(post)
            periods = list(PERIOD.finditer(body))
            if len(periods) != 1:
                print(f'SKIP {pid}: {len(periods)} unambiguous server-time periods (need 1)')
                continue
            m = periods[0]
            # Reject mixed timezone notation within this event-period segment.
            segment = body[m.start():m.end()]
            if re.search(r'UTC\s*[+-]', segment, re.I):
                print(f'SKIP {pid}: mixed timezone labels')
                continue
            start, end = m.group('start').replace('/', '-'), m.group('end').replace('/', '-')
            sd, st = jst(start, m.group('startclock'))
            ed, et = jst(end, m.group('endclock'))
            if (sd, ed) != (start, end):
                print(f'SKIP {pid}: JST date rollover needs review')
                continue
            matches = [e for e in rows if isinstance(e, dict) and e.get('game') == 'hsr'
                       and any(normalize(alias) in normalize(str(e.get(field) or ''))
                               for alias in ('次元界分裂', 'planar fissure')
                               for field in ('name', 'original_name'))
                       and (e.get('start'), e.get('end')) == (start, end)]
            if len(matches) != 1:
                print(f'SKIP {pid}: {len(matches)} existing matching events (need 1)')
                continue
            event = matches[0]
            key = str(event.get('id') or '')
            if not key or key in pending:
                print(f'SKIP {pid}: missing or duplicate event id')
                continue
            if event.get('start_label') or event.get('end_label'):
                print(f'SKIP {pid}: existing human-readable time label')
                continue
            old_url = str(event.get('official_url') or '')
            url = f'https://www.hoyolab.com/article/{pid}'
            if old_url and old_url != url:
                print(f'SKIP {pid}: existing different official source')
                continue
            pending[key] = (event, st, et, url)
            print(f'MATCH: {event.get("name")} {start} {st} JST -> {end} {et} JST | {url}')
        except Exception as exc:
            print(f'WARNING: article {pid}: {type(exc).__name__}: {exc}')
    changed = 0
    for event, st, et, url in pending.values():
        if event.get('start_time') == st and event.get('end_time') == et and event.get('official_url') == url:
            continue
        event['start_time'] = st
        event['end_time'] = et
        event['official_url'] = url
        event['source_status'] = 'HoYoLAB公式認証投稿・Asiaサーバー時刻をJST換算'
        changed += 1
    if changed:
        # Atomic replacement; preserve the original file if writing fails.
        fd, name = tempfile.mkstemp(prefix='.hsr-events-', suffix='.json', dir=ROOT)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                json.dump(rows, out, ensure_ascii=False, indent=2)
                out.write('\n')
            os.replace(name, EVENTS)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    print(f'Done: {changed} existing Planar Fissure events updated; no events added or deleted.')
    print('Assumption: Asia server time = UTC+8. Other event types remain unchanged.')


if __name__ == '__main__':
    main()
