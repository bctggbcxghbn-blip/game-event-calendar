#!/usr/bin/env python3
"""Remove duplicate ZZZ calendar records after all importers have run.

Only records with matching normalized title and exact start/end dates are
merged. Prefer an official-source record when one exists.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def normalized_name(name):
    name = str(name or '').strip()
    name = re.sub(r'\s+(?:Event Details|Event Notice|Event Guide)$', '', name, flags=re.I)
    name = name.strip().strip('"“”‘’').strip()
    return re.sub(r'\s+', ' ', name).casefold()


def official(record):
    return bool(record.get('official_url')) or str(record.get('id', '')).startswith('zzz-official-')


def deduplicate(events):
    winners = {}
    for index, event in enumerate(events):
        if not isinstance(event, dict) or event.get('game') != 'zzz':
            continue
        key = (normalized_name(event.get('name')), event.get('start'), event.get('end'))
        previous = winners.get(key)
        if previous is None or (official(event) and not official(events[previous])):
            winners[key] = index
    keep = set(winners.values())
    result = []
    removed = 0
    for index, event in enumerate(events):
        if isinstance(event, dict) and event.get('game') == 'zzz' and index not in keep:
            print(f'REMOVE DUPLICATE: {event.get("name")} ({event.get("id")})')
            removed += 1
        else:
            result.append(event)
    return result, removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'events.json'
    events = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise ValueError('events.json must be a JSON array')
    cleaned, removed = deduplicate(events)
    print(f'DUPLICATES REMOVED: {removed}' if args.apply else f'DUPLICATES FOUND: {removed}')
    if args.apply and removed:
        path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('UPDATED: events.json')
    else:
        print('No files modified.')


if __name__ == '__main__':
    main()
