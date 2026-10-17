#!/usr/bin/env python3
"""Import manually verified ZZZ challenge windows from games/zzz/zzz_challenge_confirmed.json.

Only explicit, source-backed windows are imported. Predicted rotations are never imported.
Run without --apply for preview; --apply writes events.json if records qualify.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
CONFIRMED = Path(__file__).with_name('zzz_challenge_confirmed.json')
KINDS = {'式輿防衛戦・激変ノード', '危局強襲戦'}
TIME = re.compile(r'^\d{2}:\d{2}$')


def read_date(s):
    return dt.date.fromisoformat(s)


def valid_time(s):
    if not isinstance(s, str) or not TIME.fullmatch(s):
        return False
    h, m = map(int, s.split(':'))
    return h < 24 and m < 60


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not CONFIRMED.exists():
        raise SystemExit(f'Missing {CONFIRMED.relative_to(ROOT)}; create it from the supplied template.')
    rows = json.loads(CONFIRMED.read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise SystemExit('Confirmed file must be a JSON array')
    events_path = ROOT / 'events.json'
    events = json.loads(events_path.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise SystemExit('events.json must be a JSON array')
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    existing_ids = {str(e.get('id')) for e in events if isinstance(e, dict)}
    additions = []
    for index, row in enumerate(rows, 1):
        try:
            if not isinstance(row, dict) or row.get('name') not in KINDS:
                raise ValueError('unknown challenge name')
            if row.get('source_status') != 'official_confirmed':
                raise ValueError('source_status must be official_confirmed')
            url = row['official_url']
            parsed = urlparse(url)
            if parsed.scheme != 'https' or parsed.hostname not in ('hoyolab.com', 'www.hoyolab.com', 'zenless.hoyoverse.com'):
                raise ValueError('official_url must be an official HoYoLAB/ZZZ HTTPS link')
            start = read_date(row['start'])
            end = read_date(row['end'])
            if end < start or (end - start).days > 60:
                raise ValueError('invalid date range')
            if not valid_time(row['start_time']) or not valid_time(row['end_time']):
                raise ValueError('invalid HH:MM time')
            end_dt = dt.datetime.combine(end, dt.time.fromisoformat(row['end_time']), tzinfo=now.tzinfo)
            if end_dt < now:
                print(f'SKIP row {index}: already ended')
                continue
            if start > now.date() + dt.timedelta(days=120):
                print(f'SKIP row {index}: more than 120 days ahead')
                continue
            kind_slug = 'shiyu' if row['name'].startswith('式輿') else 'deadly-assault'
            identifier = f'zzz-challenge-{kind_slug}-{start:%Y%m%d}'
            if identifier in existing_ids or any(
                isinstance(e, dict) and e.get('game') == 'zzz'
                and e.get('name') == row['name'] and e.get('start') == start.isoformat()
                for e in events + additions
            ):
                print(f'SKIP row {index}: duplicate')
                continue
            record = {
                'id': identifier, 'game': 'zzz', 'name': row['name'],
                'start': start.isoformat(), 'end': end.isoformat(),
                'start_time': row['start_time'], 'end_time': row['end_time'],
                'time_zone': 'Asia/Tokyo', 'kind': 'チャレンジ',
                'source_status': 'HoYoLAB公式確認済み',
                'official_url': url, 'url': url,
            }
            additions.append(record)
            existing_ids.add(identifier)
            print(f'CANDIDATE: {record["name"]} {start} {row["start_time"]} -> {end} {row["end_time"]} JST')
        except (KeyError, TypeError, ValueError) as exc:
            print(f'SKIP row {index}: {exc}')
    if args.apply and additions:
        events.extend(additions)
        events.sort(key=lambda e: (str(e.get('start', '')), str(e.get('game', '')), str(e.get('name', ''))))
        events_path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'ADDED: {len(additions)} record(s). events.json updated.')
    else:
        print(f'{"ADDED" if args.apply else "PREVIEW"}: {len(additions)} record(s). No files modified.')
    if not rows:
        print('INFO: No officially confirmed challenge windows configured yet. Estimates are not imported.')


if __name__ == '__main__':
    main()
