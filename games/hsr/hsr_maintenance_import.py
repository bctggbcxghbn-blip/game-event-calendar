#!/usr/bin/env python3
"""Import officially confirmed HSR maintenance windows into events.json.

Add only entries with an official source. The end is an estimate, not a confirmed completion.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'events.json'

MAINTENANCE = [
    {
        'id': 'hsr-maintenance-4.6-20260928',
        'game': 'hsr',
        'name': 'Ver.4.6 アップデートメンテナンス（終了予定）',
        'start': '2026-09-28',
        'end': '2026-09-28',
        'start_time': '07:00',
        'end_time': '12:00',
        'time_zone': 'Asia/Tokyo',
        'kind': 'メンテナンス',
        'source_status': '公式発表・終了時刻は約5時間の予定',
        'official_url': 'https://hsr.hoyoverse.com/en-us/news/166468',
    }
]

def main():
    events = json.loads(PATH.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise ValueError('events.json must contain an array')
    by_id = {event['id']: event for event in events}
    for event in MAINTENANCE:
        by_id[event['id']] = event
    merged = sorted(by_id.values(), key=lambda e: (e['start'], e['game'], e['name']))
    PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Imported {len(MAINTENANCE)} official HSR maintenance record(s).')

if __name__ == '__main__':
    main()
