#!/usr/bin/env python3
"""Merge reviewed HSR maintenance records without deleting existing calendar entries.

Future official announcements must be verified and added to
`games/hsr/maintenance_verified.json`; this is NOT a live scraper.
"""
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / 'events.json'
REVIEWED = Path(__file__).with_name('maintenance_verified.json')


def validate(row):
    required = ('id', 'name', 'start', 'end', 'start_time', 'end_time', 'official_url')
    if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip() for k in required):
        raise ValueError('Incomplete maintenance record')
    if not row['id'].startswith('hsr-maintenance-'):
        raise ValueError('Unexpected maintenance id')
    start, end = dt.date.fromisoformat(row['start']), dt.date.fromisoformat(row['end'])
    if end < start or (end - start).days > 2:
        raise ValueError('Invalid maintenance date range')
    for key in ('start_time', 'end_time'):
        dt.time.fromisoformat(row[key])
    url = urlparse(row['official_url'])
    if url.scheme != 'https' or url.hostname not in ('hsr.hoyoverse.com', 'www.hoyolab.com'):
        raise ValueError('Expected official HSR source URL')
    return {**row, 'game': 'hsr', 'kind': 'メンテナンス', 'time_zone': 'Asia/Tokyo'}


def main():
    reviewed = json.loads(REVIEWED.read_text(encoding='utf-8'))
    events = json.loads(EVENTS.read_text(encoding='utf-8'))
    if not isinstance(reviewed, list) or not isinstance(events, list):
        raise ValueError('Both JSON files must contain arrays')
    by_id = {event['id']: event for event in events}
    count = 0
    for item in reviewed:
        record = validate(item)
        if record['id'] in by_id and by_id[record['id']].get('kind') != 'メンテナンス':
            raise ValueError('ID conflict: ' + record['id'])
        if by_id.get(record['id']) != record:
            by_id[record['id']] = record
            count += 1
    if count:
        merged = sorted(by_id.values(), key=lambda e: (e['start'], e['game'], e['name']))
        EVENTS.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'HSR maintenance: {count} added/updated; {len(reviewed)} reviewed records. No live discovery.')


if __name__ == '__main__':
    main()
