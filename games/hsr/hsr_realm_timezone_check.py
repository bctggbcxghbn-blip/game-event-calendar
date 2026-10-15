#!/usr/bin/env python3
"""Read-only diagnostic for Realm of the Strange event-period timezone labels."""
import datetime as dt
import re
from hsr_official_candidates import EXPECTED_UID, EXPECTED_CERT, fetch, as_text
from hsr_official_asia_apply import PERIOD

ASIA = dt.timezone(dt.timedelta(hours=8))
JST = dt.timezone(dt.timedelta(hours=9))

def convert(date, clock):
    parsed = dt.datetime.strptime(date.replace('/', '-') + ' ' + clock, '%Y-%m-%d %H:%M')
    return parsed.replace(tzinfo=ASIA).astimezone(JST).strftime('%Y-%m-%d %H:%M')

def diagnose(body):
    periods = list(PERIOD.finditer(body))
    if len(periods) != 1:
        print(f'  REVIEW: found {len(periods)} event periods; expected exactly one')
        return
    m = periods[0]
    start_zone = re.sub(r'\s+', '', m.group('startzone') or '').lower()
    end_zone = re.sub(r'\s+', '', m.group('endzone') or '').lower()
    print(f'  START: {m.group("start")} {m.group("startclock")} {m.group("startzone") or "(not specified)"}')
    print(f'  END:   {m.group("end")} {m.group("endclock")} {m.group("endzone")}')
    print('  ASIA ASSUMPTION ONLY (UTC+8 -> JST):')
    print(f'    {convert(m.group("start"), m.group("startclock"))} -> {convert(m.group("end"), m.group("endclock"))}')
    if start_zone and start_zone != end_zone:
        print('  REVIEW REQUIRED: explicit timezone labels differ; do not auto-apply')
    elif not start_zone:
        print('  REVIEW REQUIRED: start timezone is omitted; do not auto-apply')
    else:
        print('  Labels agree; still require unique matching event before any update')
    excerpt = ' '.join(body[max(0, m.start()-100):min(len(body), m.end()+160)].split())
    print('  SOURCE EXCERPT:', excerpt[:420])

def main():
    ids = {}
    for category in (1, 2, 3):
        try:
            data = fetch('getNewsList', {'gids': 6, 'type': category, 'page_size': 20})
            for entry in data.get('list') or []:
                post = entry.get('post') or {}
                title = str(post.get('subject') or '')
                pid = str(post.get('post_id') or '')
                if pid.isdigit() and title.casefold().startswith('realm of the strange event:'):
                    ids[pid] = title
        except Exception as exc:
            print(f'WARNING: category {category}: {exc}')
    print(f'Found {len(ids)} Realm of the Strange articles')
    for pid, title in ids.items():
        try:
            data = fetch('getPostFull', {'post_id': pid})
            wrapper = data.get('post') or {}
            post = wrapper.get('post') or {}
            user = wrapper.get('user') or {}
            cert = user.get('certification') or {}
            if not (str(user.get('uid')) == EXPECTED_UID and user.get('nickname') == 'Honkai: Star Rail' and isinstance(cert, dict) and cert.get('desc') == EXPECTED_CERT):
                print(f'SKIP {pid}: publisher mismatch')
                continue
            print(f'\nARTICLE: {post.get("subject") or title}')
            print(f'URL: https://www.hoyolab.com/article/{pid}')
            diagnose(as_text(post))
        except Exception as exc:
            print(f'WARNING {pid}: {type(exc).__name__}: {exc}')
    print('\nDone. events.json unchanged.')

if __name__ == '__main__':
    main()
