#!/usr/bin/env python3
"""Zenless Zone Zero official HoYoLAB importer. Preview by default; --apply writes.

Uses HSR HoYoLAB helpers already present in this repository. Server-time dates
are preserved as dates only: server time must not be assumed to be JST.
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
from hsr_maintenance_time_preview import content_text  # noqa: E402

JST = dt.timezone(dt.timedelta(hours=9))
GID = '8'
DATE = r'20\d{2}[/-]\d{1,2}[/-]\d{1,2}'
CLOCK = r'\d{1,2}:\d{2}(?::\d{2})?'
STAMP = rf'({DATE})\s+({CLOCK})\s*(?:\(\s*(?:server\s*time|UTC\s*\+\s*8)\s*\))?'
RANGE = re.compile(rf'{STAMP}\s*(?:-|–|—|~|～|to)\s*{STAMP}', re.I)
EXPLICIT_TZ = re.compile(r'UTC\s*\+\s*8', re.I)
GACHA = re.compile(r'limited.time channels?|signal search|exclusive channel|変調|独占チャンネル|限定チャンネル|调频|独家频段', re.I)
CHALLENGE = re.compile(r'shiyu defense|deadly assault|hollow zero|式輿防衛戦|危局強襲戦|零号ホロウ|式舆防卫战|危局强袭战', re.I)
MAINTENANCE = re.compile(r'maintenance|メンテナンス|维护|停服', re.I)
EVENT = re.compile(r'event|login|limited.time|イベント|ログイン|活动|签到', re.I)
LABEL = re.compile(r'event duration|event period|signal search event period|maintenance duration|duration\s*:', re.I)


def classify(title):
    if GACHA.search(title):
        return 'ガチャ'
    if CHALLENGE.search(title):
        return 'チャレンジ'
    if MAINTENANCE.search(title):
        return 'メンテナンス'
    if EVENT.search(title):
        return 'イベント'
    return None


def as_date(raw):
    return dt.date(*[int(x) for x in raw.replace('/', '-').split('-')])


def window(body, kind):
    """Find an explicit pair of dated endpoints, not update-relative starts."""
    matches = []
    for match in RANGE.finditer(body):
        try:
            start, end = as_date(match.group(1)), as_date(match.group(3))
        except ValueError:
            continue
        if start > end or (end-start).days > 120:
            continue
        before = body[max(0, match.start()-170):match.start()]
        if not (LABEL.search(before) or (kind == 'ガチャ' and 'signal search' in before.lower())):
            continue
        # For announcements that mix trial stages with banners, prefer the
        # first signal-search schedule. Never infer a missing update date.
        matches.append((start, end, match.group(0)))
    if not matches:
        return None, 'No explicit labelled start/end dates'
    if kind == 'ガチャ':
        return matches[0], None
    distinct = {(a, b) for a, b, _ in matches}
    if len(distinct) != 1:
        return None, f'Ambiguous date ranges ({len(distinct)})'
    return matches[0], None


def articles(limit):
    seen = set()
    for typ in (1, 2, 3):
        try:
            response = get_json(LIST + '?' + urlencode({'gids': GID, 'type': typ, 'page_size': limit}))
            items = response.get('list', [])
            if not isinstance(items, list):
                raise ValueError('Unexpected list response')
            print(f'NEWS TYPE {typ}: {len(items)} articles')
        except Exception as exc:
            print(f'WARNING TYPE {typ}: {type(exc).__name__}: {exc}')
            continue
        for item in items:
            post = item.get('post', item) if isinstance(item, dict) else {}
            if not isinstance(post, dict):
                continue
            pid = str(post.get('post_id') or post.get('id') or '')
            title = str(post.get('subject') or post.get('title') or '')
            if pid.isdigit() and pid not in seen:
                seen.add(pid)
                kind = classify(title)
                if kind:
                    yield pid, title, kind


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Write candidates to events.json')
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()
    if not 1 <= args.limit <= 50:
        parser.error('--limit must be 1..50')
    path = ROOT / 'events.json'
    events = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise ValueError('events.json must be a JSON array')
    ids = {str(e.get('id')) for e in events if isinstance(e, dict)}
    signatures = {(e.get('game'), str(e.get('name', '')).casefold(), e.get('start')) for e in events if isinstance(e, dict)}
    today = dt.datetime.now(JST).date()
    additions = []
    counts = {}
    for pid, title, kind in articles(args.limit):
        counts[kind] = counts.get(kind, 0) + 1
        try:
            detail = get_json(DETAIL + '?' + urlencode({'post_id': pid}))
            outer = detail.get('post', {}) if isinstance(detail, dict) else {}
            post = outer.get('post', outer) if isinstance(outer, dict) else {}
            if not isinstance(post, dict) or str(post.get('game_id', GID)) != GID:
                print(f'SKIP {pid}: wrong game ID')
                continue
            parsed, reason = window(content_text(detail), kind)
            if not parsed:
                print(f'SKIP {pid} [{kind}]: {reason}')
                continue
            start, end, source_range = parsed
            if end < today:
                print(f'SKIP {pid} [{kind}]: Already ended')
                continue
            if start > today + dt.timedelta(days=120):
                print(f'SKIP {pid}: Beyond 120 days')
                continue
            event_id = f'zzz-official-{pid}-{kind}'
            signature = ('zzz', title.casefold(), start.isoformat())
            if event_id in ids or signature in signatures:
                print(f'SKIP {pid}: Already recorded')
                continue
            url = f'https://www.hoyolab.com/article/{pid}'
            event = {'id': event_id, 'game': 'zzz', 'name': title,
                     'start': start.isoformat(), 'end': end.isoformat(),
                     'kind': kind, 'source_status': 'HoYoLAB公式・日付のみ（サーバー時刻の地域差を考慮）',
                     'official_url': url, 'url': url}
            additions.append(event)
            ids.add(event_id)
            signatures.add(signature)
            print(f'CANDIDATE [{kind}] {start} -> {end} {title[:110]}')
        except Exception as exc:
            print(f'WARNING {pid}: {type(exc).__name__}: {str(exc)[:150]}')
    print(f'CLASSIFICATION COUNTS: {counts}')
    if args.apply and additions:
        events.extend(additions)
        events.sort(key=lambda e: (e.get('start', ''), e.get('game', ''), e.get('name', '')))
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{"ADDED" if args.apply else "PREVIEW"}: {len(additions)} record(s). ' + ('events.json updated.' if args.apply and additions else 'No files modified.'))


if __name__ == '__main__':
    main()
