#!/usr/bin/env python3
"""Conservative Genshin official-news importer. Preview unless --apply.

Requires the existing games/hsr HoYoLAB helper scripts. Never guesses dates.
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
from hsr_maintenance_detail_probe import DETAIL, LIST, get_json  # noqa: E402
from hsr_maintenance_time_preview import content_text, parse_window  # noqa: E402

EVENTS = ROOT / 'events.json'
JST = dt.timezone(dt.timedelta(hours=9))
NEWS_PARAMS = {'gids': '2', 'type': '1', 'page_size': '50'}
DATE = re.compile(r'(?<!\d)(20\d{2})[/-](\d{1,2})[/-](\d{1,2})(?!\d)')
TIME = re.compile(r'(?<!\d)(\d{1,2}):(\d{2})\s*\(?\s*(?:UTC|GMT)\s*\+\s*8\s*\)?', re.I)
RANGE = re.compile(r'(?<!\d)(20\d{2}[/-]\d{1,2}[/-]\d{1,2})\s+(\d{1,2}:\d{2})\s*\(?\s*(?:UTC|GMT)\s*\+\s*8\s*\)?\s*(?:-|–|—|~|～|to|until)\s*(20\d{2}[/-]\d{1,2}[/-]\d{1,2})\s+(\d{1,2}:\d{2})\s*\(?\s*(?:UTC|GMT)\s*\+\s*8\s*\)?', re.I)
CLASSIFY = [
    ('ガチャ', re.compile(r'event wish|character event wish|weapon event wish|祈愿|祈願|祈愿活动|祈願イベント', re.I)),
    ('チャレンジ', re.compile(r'spiral abyss|imaginarium theater|stygian onslaught|深境螺旋|幻想シアター|幽境の激戦|幻想真境劇詩', re.I)),
    ('メンテナンス', re.compile(r'maintenance|维护公告|停服更新|メンテナンス', re.I)),
    ('イベント', re.compile(r'event|web event|login|イベント|活动|ログイン|update notice|update details|version.*update', re.I)),
]

def classify(title):
    return next((kind for kind, pattern in CLASSIFY if pattern.search(title)), None)

def convert(date, clock):
    values = [int(x) for x in date.replace('/', '-').split('-')]
    hour, minute = [int(x) for x in clock.split(':')]
    return dt.datetime(*values, hour, minute, tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(JST)

def explicit_range(body):
    """Accept only an unambiguous UTC+8 full date+time range."""
    found = []
    for match in RANGE.finditer(body):
        try:
            start, end = convert(match.group(1), match.group(2)), convert(match.group(3), match.group(4))
            if start < end and end - start <= dt.timedelta(days=120):
                found.append((start, end))
        except ValueError:
            pass
    return found[0] if len(found) == 1 else None

def news():
    data = get_json(LIST + '?' + urlencode(NEWS_PARAMS))
    items = data.get('list') if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ValueError('Unexpected news response')
    seen = set()
    for item in items:
        post = item.get('post', item) if isinstance(item, dict) else None
        if not isinstance(post, dict):
            continue
        pid = str(post.get('post_id') or post.get('id') or '')
        title = str(post.get('subject') or post.get('title') or '')
        if pid.isdigit() and pid not in seen and classify(title):
            seen.add(pid)
            yield pid, title

def make_event(pid, title, now, diagnose=False):
    detail = get_json(DETAIL + '?' + urlencode({'post_id': pid}))
    outer = detail.get('post', {}) if isinstance(detail, dict) else {}
    post = outer.get('post', outer) if isinstance(outer, dict) else {}
    if not isinstance(post, dict) or str(post.get('game_id', '2')) != '2':
        return None, 'Game ID mismatch'
    body = content_text(detail)
    kind = classify(title)
    if diagnose:
        diagnose_article(pid, title, kind, body)
    if kind == 'メンテナンス':
        window, reason = parse_window(body)
        if not window:
            return None, reason
        start, end, hours = window
        name = title + '（終了予定）'
        status = f'HoYoLAB公式記事・終了は約{hours}時間後の予定'
    else:
        # News roundup articles may contain many ranges; never attach one to
        # the entire article unless it is the only explicit UTC+8 range.
        window = explicit_range(body)
        if not window:
            return None, 'No single explicit UTC+8 start/end range'
        start, end = window
        name = title
        status = 'HoYoLAB公式記事・UTC+8日時をJST換算（要確認）'
    if end <= now:
        return None, 'Already ended'
    if start > now + dt.timedelta(days=120):
        return None, 'Beyond 120-day window'
    url = f'https://www.hoyolab.com/article/{pid}'
    return {
        'id': f'genshin-official-{pid}-{hashlib.sha1((kind + name).encode()).hexdigest()[:8]}',
        'game': 'genshin', 'name': name, 'start': start.date().isoformat(),
        'end': end.date().isoformat(), 'kind': kind,
        'start_time': start.strftime('%H:%M'), 'end_time': end.strftime('%H:%M'),
        'time_zone': 'Asia/Tokyo', 'source_status': status,
        'official_url': url, 'url': url,
    }, None

def diagnose_article(pid, title, kind, body):
    """Print bounded date/time contexts to diagnose official formatting; no writes."""
    print(f'DIAG ARTICLE {pid} [{kind}] {title[:130]}', flush=True)
    print(f'DIAG BODY length={len(body)}', flush=True)
    # Include only contexts containing dates, UTC offsets, or schedule terms.
    # Keep output bounded so Actions logs stay manageable.
    pattern = re.compile(r'20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}|UTC\s*[+＋]\s*8|GMT\s*[+＋]\s*8|server time|maintenance|event duration|event wish|期間|时间|時間', re.I)
    shown = 0
    for match in pattern.finditer(body):
        fragment = re.sub(r'\s+', ' ', body[max(0, match.start()-95):match.end()+145]).strip()
        if fragment:
            print('DIAG CONTEXT:', fragment[:240], flush=True)
            shown += 1
        if shown >= 6:
            break
    if not shown:
        print('DIAG CONTEXT: no date/time markers found', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Write safe candidates to events.json')
    parser.add_argument('--diagnose', action='store_true', help='Print article titles and date/time contexts (read only)')
    args = parser.parse_args()
    if args.apply and args.diagnose:
        parser.error('--diagnose cannot be combined with --apply')
    events = json.loads(EVENTS.read_text(encoding='utf-8'))
    if not isinstance(events, list) or any(not isinstance(e, dict) or not e.get('id') for e in events):
        raise ValueError('Invalid events.json')
    ids = {e['id'] for e in events}
    # Only same name and start date is considered a duplicate; do not discard
    # distinct events merely because they start on the same day.
    signatures = {(e.get('game'), str(e.get('name', '')).casefold(), e.get('start')) for e in events}
    try:
        articles = list(news())
    except Exception as exc:
        print(f'WARNING: Genshin news unavailable: {type(exc).__name__}: {exc}')
        return
    print(f'Genshin all categories: checking {len(articles)} official notice(s)')
    print('CLASSIFICATION COUNTS:', {kind: sum(classify(t) == kind for _, t in articles) for kind, _ in CLASSIFY})
    additions = []
    now = dt.datetime.now(JST)
    for pid, title in articles:
        try:
            event, reason = make_event(pid, title, now, diagnose=args.diagnose)
            if not event:
                print(f'SKIP {pid} [{classify(title)}]: {reason}')
                continue
            signature = (event['game'], event['name'].casefold(), event['start'])
            if event['id'] in ids or signature in signatures:
                print(f'SKIP {pid}: Already recorded')
                continue
            additions.append(event)
            ids.add(event['id'])
            signatures.add(signature)
            print(f'CANDIDATE [{event["kind"]}] {event["start"]} {event["name"]} | {event["url"]}')
        except Exception as exc:
            print(f'WARNING {pid}: {type(exc).__name__}: {str(exc)[:150]}')
    if args.apply and additions:
        merged = sorted(events + additions, key=lambda e: (e['start'], e.get('game', ''), e.get('name', '')))
        EVENTS.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{"ADDED" if args.apply else "PREVIEW"}: {len(additions)} record(s). ' + ('Updated events.json.' if args.apply and additions else 'No files modified.'))

if __name__ == '__main__':
    main()
