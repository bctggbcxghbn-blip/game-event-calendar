#!/usr/bin/env python3
"""Genshin maintenance discovery using HoYoLAB news. Preview by default.

Uses the already tested HoYoLAB HTTP/text/time helpers in games/hsr.
Only future official notices with explicit UTC+8 maintenance start and duration
are eligible. Undocumented API; failures do not change events.json.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'games' / 'hsr'))
from hsr_maintenance_detail_probe import DETAIL, LIST, get_json  # noqa: E402
from hsr_maintenance_time_preview import content_text, parse_window  # noqa: E402

EVENTS = ROOT / 'events.json'
JST = dt.timezone(dt.timedelta(hours=9))
PARAMS = {'gids': '2', 'type': '1', 'page_size': '50'}
TITLE = re.compile(r'(?:maintenance|update notice|update details|维护公告|维护预告|停服更新)', re.I)


def discover():
    data = get_json(LIST + '?' + urlencode(PARAMS))
    items = data.get('list', []) if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ValueError('Unexpected Genshin news response')
    seen = set()
    for item in items:
        post = item.get('post', item) if isinstance(item, dict) else None
        if not isinstance(post, dict):
            continue
        title = str(post.get('subject') or post.get('title') or '')
        pid = str(post.get('post_id') or post.get('id') or '')
        if pid.isdigit() and pid not in seen and TITLE.search(title):
            seen.add(pid)
            yield pid, title


def candidate(pid, title, now):
    detail = get_json(DETAIL + '?' + urlencode({'post_id': pid}))
    # Do not trust a non-Genshin article returned by the API.
    outer = detail.get('post', {}) if isinstance(detail, dict) else {}
    post = outer.get('post', outer) if isinstance(outer, dict) else {}
    if not isinstance(post, dict) or str(post.get('game_id', '2')) != '2':
        return None, 'Article game ID mismatch'
    body = content_text(detail)
    window, reason = parse_window(body)
    if not window:
        return None, reason
    start, end, hours = window
    if not now < start <= now + dt.timedelta(days=120):
        return None, 'Outside future 120-day window'
    version = re.search(r'\bVersion\s+(\d+(?:\.\d+)?)\b', title, re.I)
    label = f'Ver.{version.group(1)}' if version else '原神'
    url = f'https://www.hoyolab.com/article/{pid}'
    return {
        'id': f'genshin-maintenance-official-{pid}',
        'game': 'genshin',
        'name': f'{label} アップデートメンテナンス（終了予定）',
        'start': start.date().isoformat(),
        'end': end.date().isoformat(),
        'start_time': start.strftime('%H:%M'),
        'end_time': end.strftime('%H:%M'),
        'time_zone': 'Asia/Tokyo',
        'kind': 'メンテナンス',
        'source_status': f'HoYoLAB公式記事・終了時刻は約{hours}時間後の予定',
        'official_url': url,
        'url': url,
    }, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    events = json.loads(EVENTS.read_text(encoding='utf-8'))
    if not isinstance(events, list) or not all(isinstance(e, dict) and 'id' in e for e in events):
        raise ValueError('Invalid events.json')
    ids = {e['id'] for e in events}
    dates = {e.get('start') for e in events if e.get('game') == 'genshin' and e.get('kind') == 'メンテナンス'}
    now = dt.datetime.now(JST)
    try:
        articles = list(discover())
    except Exception as exc:
        print(f'WARNING: Genshin news unavailable: {type(exc).__name__}: {exc}')
        return
    print(f'Genshin maintenance: checking {len(articles)} candidate notice(s)')
    additions = []
    for pid, title in articles[:20]:
        try:
            event, reason = candidate(pid, title, now)
            if not event:
                print(f'SKIP {pid}: {reason}')
                continue
            if event['id'] in ids or event['start'] in dates:
                print(f'SKIP {pid}: already recorded (ID or date)')
                continue
            print(f'CANDIDATE {event["start"]} {event["start_time"]}–{event["end_time"]} JST | {event["url"]}')
            additions.append(event)
            ids.add(event['id'])
            dates.add(event['start'])
        except Exception as exc:
            print(f'WARNING: Article {pid}: {type(exc).__name__}: {exc}')
    if args.apply and additions:
        merged = sorted(events + additions, key=lambda e: (e['start'], e['game'], e['name']))
        EVENTS.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{"ADDED" if args.apply else "PREVIEW"}: {len(additions)} future maintenance record(s). '
          f'{"Updated events.json." if args.apply and additions else "No files modified."}')


if __name__ == '__main__':
    main()
