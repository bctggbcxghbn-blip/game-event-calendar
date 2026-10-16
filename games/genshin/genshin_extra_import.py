#!/usr/bin/env python3
"""Import official Genshin event, wish and challenge dates; preview by default.

UTC+8 is converted to JST only when explicitly given. Unlabelled in-game
schedule times are saved as dates only, without claiming a timezone.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'games' / 'hsr'))
from hsr_maintenance_detail_probe import LIST, DETAIL, get_json  # noqa: E402
from hsr_maintenance_time_preview import content_text  # noqa: E402

JST = dt.timezone(dt.timedelta(hours=9))
UTC8 = dt.timezone(dt.timedelta(hours=8))
WISH = re.compile(r'event wishes? notice|event wish(?:es)?\b|祈願|祈愿', re.I)
CHALLENGE = re.compile(r'spiral abyss|imaginarium theater|stygian onslaught|深境螺旋|幻想シアター|幻想真境劇詩|幽境の激戦', re.I)
EVENT = re.compile(r'events? preview|event[:：]|web event|login event|イベント|活动|double drops|overflowing', re.I)
NUM_DATE = r'20\d{2}[/-]\d{1,2}[/-]\d{1,2}'
CLOCK = r'\d{1,2}:\d{2}(?::\d{2})?'
NUM_RANGE = re.compile(rf'({NUM_DATE})\s+({CLOCK})\s*(?:-|–|—|~|～|to)\s*({NUM_DATE})\s+({CLOCK})', re.I)
MONTH = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
EN_RANGE = re.compile(rf'({MONTH}\s+\d{{1,2}},?\s+20\d{{2}})\s*(?:-|–|—|to)\s*({MONTH}\s+\d{{1,2}},?\s+20\d{{2}})\s*({CLOCK})?', re.I)
TZ = re.compile(r'\(\s*(?:UTC|GMT)\s*\+\s*8\s*\)', re.I)
DURATION = re.compile(r'(?:event wish duration|event duration|event time|challenge duration|maintenance duration|活动时间)', re.I)


def category(title):
    if WISH.search(title):
        return 'ガチャ'
    if CHALLENGE.search(title):
        return 'チャレンジ'
    if EVENT.search(title):
        return 'イベント'
    return None


def parse_num_date(value):
    return dt.date.fromisoformat('-'.join(f'{int(x):02d}' if i else x for i, x in enumerate(value.replace('/', '-').split('-'))))


def parse_english(value):
    cleaned = value.replace(',', '')
    return dt.datetime.strptime(cleaned, '%B %d %Y').date()


def parse_window(body):
    """Use first labelled Event Duration, not unrelated reward/result dates."""
    headings = list(DURATION.finditer(body))
    # Wish articles can have several banner blocks with identical windows.
    windows = []
    for heading in headings:
        section = body[heading.end():heading.end()+230]
        n = NUM_RANGE.search(section)
        e = EN_RANGE.search(section)
        if n and (not e or n.start() < e.start()):
            start_date, end_date = parse_num_date(n.group(1)), parse_num_date(n.group(3))
            start_clock, end_clock = n.group(2), n.group(4)
            tail = section[n.end():n.end()+35]
            # If the official notice explicitly labels UTC+8 for the range,
            # convert times and dates to JST. Otherwise do not invent zone.
            explicit = bool(TZ.search(tail) or TZ.search(section[max(0,n.start()-12):n.start()]))
            if explicit:
                st = dt.datetime.fromisoformat(f'{start_date}T{start_clock}').replace(tzinfo=UTC8).astimezone(JST)
                en = dt.datetime.fromisoformat(f'{end_date}T{end_clock}').replace(tzinfo=UTC8).astimezone(JST)
                windows.append((st.date(), en.date(), st.strftime('%H:%M'), en.strftime('%H:%M'), True))
            else:
                windows.append((start_date, end_date, None, None, False))
        elif e:
            start_date, end_date = parse_english(e.group(1)), parse_english(e.group(2))
            clock = e.group(3)
            tail = section[e.end():e.end()+40]
            explicit = bool(TZ.search(tail))
            if explicit and clock:
                # Start time is unspecified: preserve only calendar dates.
                end_dt = dt.datetime.fromisoformat(f'{end_date}T{clock}').replace(tzinfo=UTC8).astimezone(JST)
                windows.append((start_date, end_dt.date(), None, end_dt.strftime('%H:%M'), False))
            else:
                windows.append((start_date, end_date, None, None, False))
    if not windows:
        return None, 'No labelled event duration found'
    distinct = list(dict.fromkeys(windows))
    if len(distinct) > 1:
        return None, f'Ambiguous duration: {len(distinct)} different windows'
    window = distinct[0]
    if window[0] > window[1] or (window[1] - window[0]).days > 120:
        return None, 'Invalid or excessive duration'
    return window, None


def fetch_articles(limit):
    seen = set()
    for typ in (1, 2, 3):
        try:
            data = get_json(LIST + '?' + urlencode({'gids': '2', 'type': str(typ), 'page_size': str(limit)}))
            items = data.get('list', [])
            if not isinstance(items, list):
                raise ValueError('Unexpected list response')
            print(f'NEWS TYPE {typ}: {len(items)} articles')
        except Exception as exc:
            print(f'WARNING TYPE {typ}: {exc}')
            continue
        for item in items:
            post = item.get('post', item) if isinstance(item, dict) else {}
            if not isinstance(post, dict):
                continue
            pid = str(post.get('post_id') or post.get('id') or '')
            title = str(post.get('subject') or post.get('title') or '')
            kind = category(title)
            if pid.isdigit() and pid not in seen and kind:
                seen.add(pid)
                yield pid, title, kind


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()
    if not 1 <= args.limit <= 50:
        parser.error('--limit must be 1..50')
    path = ROOT / 'events.json'
    events = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise ValueError('events.json must contain a list')
    existing = {str(e.get('id')) for e in events if isinstance(e, dict)}
    signatures = {(e.get('game'), str(e.get('name', '')).casefold(), e.get('start')) for e in events if isinstance(e, dict)}
    today = dt.datetime.now(JST).date()
    added = []
    for pid, title, kind in fetch_articles(args.limit):
        try:
            detail = get_json(DETAIL + '?' + urlencode({'post_id': pid}))
            outer = detail.get('post', {})
            post = outer.get('post', outer) if isinstance(outer, dict) else {}
            if str(post.get('game_id', '2')) != '2':
                print(f'SKIP {pid}: wrong game')
                continue
            window, reason = parse_window(content_text(detail))
            if not window:
                print(f'SKIP {pid} [{kind}]: {reason}')
                continue
            start, end, start_time, end_time, tz_explicit = window
            if end < today:
                print(f'SKIP {pid} [{kind}]: Already ended')
                continue
            if start > today + dt.timedelta(days=120):
                print(f'SKIP {pid}: Too far ahead')
                continue
            name = title
            event_id = f'genshin-extra-{pid}-{hashlib.sha1((kind+name).encode()).hexdigest()[:8]}'
            signature = ('genshin', name.casefold(), start.isoformat())
            if event_id in existing or signature in signatures:
                print(f'SKIP {pid}: Already recorded')
                continue
            url = f'https://www.hoyolab.com/article/{pid}'
            event = {'id': event_id, 'game': 'genshin', 'name': name, 'start': start.isoformat(),
                     'end': end.isoformat(), 'kind': kind,
                     'source_status': ('HoYoLAB公式・UTC+8から日本時間に換算' if tz_explicit else 'HoYoLAB公式・日付のみ（地域別時刻は未確定）'),
                     'official_url': url, 'url': url}
            if start_time:
                event['start_time'] = start_time
            if end_time and tz_explicit:
                event['end_time'] = end_time
            if tz_explicit:
                event['time_zone'] = 'Asia/Tokyo'
            added.append(event)
            existing.add(event_id)
            signatures.add(signature)
            print(f'CANDIDATE [{kind}] {start} -> {end} {title[:90]}')
        except Exception as exc:
            print(f'WARNING {pid}: {type(exc).__name__}: {str(exc)[:160]}')
    if args.apply and added:
        events.extend(added)
        events.sort(key=lambda e: (e.get('start', ''), e.get('game', ''), e.get('name', '')))
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{"ADDED" if args.apply else "PREVIEW"}: {len(added)} record(s). ' + ('events.json updated.' if args.apply and added else 'No files modified.'))


if __name__ == '__main__':
    main()
