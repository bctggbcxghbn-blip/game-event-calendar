#!/usr/bin/env python3
"""Conservative HSR maintenance auto-import. Default: read-only preview.

Use --apply only after inspecting preview logs. Existing maintenance entries,
including manually reviewed ones, are never overwritten. API is undocumented.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlencode

from hsr_maintenance_detail_probe import DETAIL, LIST, PARAMS, get_json
from hsr_maintenance_time_preview import TITLE, content_text, parse_window

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / 'events.json'
JST = dt.timezone(dt.timedelta(hours=9))


def discover():
    data = get_json(LIST + '?' + urlencode(PARAMS))
    items = data.get('list', []) if isinstance(data, dict) else []
    if not isinstance(items, list):
        raise ValueError('Unexpected news list format')
    seen = set()
    for item in items:
        post = item.get('post', item) if isinstance(item, dict) else None
        if not isinstance(post, dict):
            continue
        title = str(post.get('subject') or post.get('title') or '')
        pid = str(post.get('post_id') or post.get('id') or '')
        if not TITLE.search(title) or not pid.isdigit() or pid in seen:
            continue
        seen.add(pid)
        yield pid, title


def candidate(pid, title, now):
    detail = get_json(DETAIL + '?' + urlencode({'post_id': pid}))
    text = content_text(detail)
    window, reason = parse_window(text)
    if not window:
        return None, reason
    start, end, hours = window
    if not (now < start <= now + dt.timedelta(days=120)):
        return None, 'Outside future 120-day window'
    # Use the article ID as a stable key, but never overwrite reviewed records.
    version = __import__('re').search(r'\bVersion\s+(\d+(?:\.\d+)?)\b', title, __import__('re').I)
    label = f'Ver.{version.group(1)}' if version else 'スタレ'
    url = f'https://www.hoyolab.com/article/{pid}'
    return {
        'id': f'hsr-maintenance-official-{pid}',
        'game': 'hsr',
        'name': f'{label} アップデートメンテナンス（終了予定）',
        'start': start.date().isoformat(),
        'end': end.date().isoformat(),
        'start_time': start.strftime('%H:%M'),
        'end_time': end.strftime('%H:%M'),
        'time_zone': 'Asia/Tokyo',
        'kind': 'メンテナンス',
        'source_status': f'公式記事・終了時刻は約{hours}時間後の予定',
        'official_url': url,
        'url': url,
    }, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Write newly verified future events to events.json')
    args = parser.parse_args()
    now = dt.datetime.now(JST)
    events = json.loads(EVENTS.read_text(encoding='utf-8'))
    if not isinstance(events, list) or not all(isinstance(e, dict) and 'id' in e for e in events):
        raise ValueError('Invalid events.json')
    existing_ids = {e['id'] for e in events}
    occupied_dates = {e.get('start') for e in events if e.get('game') == 'hsr' and e.get('kind') == 'メンテナンス'}
    additions = []
    try:
        articles = list(discover())
    except Exception as exc:
        print(f'WARNING: News list unavailable: {type(exc).__name__}: {exc}')
        return
    print(f'HSR maintenance: checking {len(articles)} official notice(s)')
    for pid, title in articles[:10]:
        try:
            record, reason = candidate(pid, title, now)
            if record is None:
                print(f'SKIP {pid}: {reason}')
                continue
            if record['id'] in existing_ids or record['start'] in occupied_dates:
                print(f'SKIP {pid}: already recorded (ID or date)')
                continue
            print(f'CANDIDATE {record["start"]} {record["start_time"]}–{record["end_time"]} JST | {record["official_url"]}')
            additions.append(record)
            existing_ids.add(record['id'])
            occupied_dates.add(record['start'])
        except Exception as exc:
            print(f'WARNING: Could not parse article {pid}: {type(exc).__name__}: {exc}')
    if args.apply and additions:
        merged = sorted(events + additions, key=lambda e: (e['start'], e['game'], e['name']))
        EVENTS.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{"ADDED" if args.apply else "PREVIEW"}: {len(additions)} future maintenance record(s). '
          f'{"Updated events.json." if args.apply and additions else "No files modified."}')


if __name__ == '__main__':
    main()
