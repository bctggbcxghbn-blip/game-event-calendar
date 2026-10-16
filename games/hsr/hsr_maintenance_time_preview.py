#!/usr/bin/env python3
"""Read-only preview: extract HSR maintenance windows from HoYoLAB notices.

Only explicit maintenance start times with UTC+8 and an explicit duration are
accepted. Never modifies events.json. API endpoints may change.
"""
import datetime as dt
import json
import re
import urllib.parse
from hsr_maintenance_detail_probe import BASE, DETAIL, LIST, PARAMS, get_json, plain

JST = dt.timezone(dt.timedelta(hours=9))
UTC8 = dt.timezone(dt.timedelta(hours=8))
TITLE = re.compile(r'(?:update and maintenance notice|maintenance notice|维护公告|维护预告)', re.I)
DATE = r'(20\d{2})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{2})'
START = re.compile(r'(?:update\s+time\s+begins\s+at|maintenance\s+(?:will\s+begin|begins|starts|start\s+time)\s*(?:at|:)?|维护(?:开始)?时间\s*[:：]?)\s*' + DATE + r'\s*\(?\s*UTC\s*\+\s*8\s*\)?', re.I)
DURATION = re.compile(r'(?:approximately|about|around|roughly)\s*(\d{1,2})\s*hours?|(?:预计|约)\s*(\d{1,2})\s*小时', re.I)

def extract_structured(raw):
    """Extract only textual inserts from HoYoLAB structured_content JSON."""
    if not isinstance(raw, str) or not raw.strip():
        return ''
    try:
        operations = json.loads(raw)
    except (ValueError, TypeError):
        return ''
    if not isinstance(operations, list):
        return ''
    chunks = []
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        insert = operation.get('insert')
        if isinstance(insert, str):
            chunks.append(insert)
        # Images and other embedded objects do not establish a maintenance time.
    return plain(' '.join(chunks))


def content_text(detail):
    if not isinstance(detail, dict):
        return ''
    outer = detail.get('post')
    if not isinstance(outer, dict):
        return ''
    post = outer.get('post') if isinstance(outer.get('post'), dict) else outer

    # Newer official articles can have content='en-us' rather than HTML.
    # structured_content carries the real text for both observed versions.
    structured = extract_structured(post.get('structured_content'))
    if structured:
        return structured

    raw = post.get('content')
    if isinstance(raw, (dict, list)):
        raw = json.dumps(raw, ensure_ascii=False)
    if not isinstance(raw, str) or not raw.strip():
        return ''
    try:
        decoded = json.loads(raw)
        if isinstance(decoded, (dict, list)):
            raw = json.dumps(decoded, ensure_ascii=False)
    except (ValueError, TypeError):
        pass
    if re.fullmatch(r'[a-z]{2}-[a-z]{2}', raw.strip(), re.I):
        return ''  # Language marker, not article body.
    return plain(raw)

def parse_window(text):
    start_match = START.search(text)
    if not start_match:
        return None, 'No explicit maintenance start with UTC+8'
    try:
        values = list(map(int, start_match.groups()))
        start = dt.datetime(*values, tzinfo=UTC8)
    except ValueError:
        return None, 'Invalid start timestamp'
    # Restrict duration to update/maintenance context, not unrelated event times.
    context = text[start_match.end():start_match.end() + 500]
    duration_match = DURATION.search(context)
    if not duration_match:
        return None, 'No explicit approximate duration near start'
    hours = int(next(g for g in duration_match.groups() if g))
    if not 1 <= hours <= 12:
        return None, 'Duration outside safe range'
    return (start.astimezone(JST), (start + dt.timedelta(hours=hours)).astimezone(JST), hours), None

def main():
    print('HSR maintenance time preview — READ ONLY', flush=True)
    try:
        data = get_json(LIST + '?' + urllib.parse.urlencode(PARAMS))
        items = data.get('list', []) if isinstance(data, dict) else []
    except Exception as exc:
        print(f'WARNING: Could not retrieve news list: {type(exc).__name__}: {str(exc)[:150]}', flush=True)
        return
    count = 0
    for item in items:
        post = item.get('post', item) if isinstance(item, dict) else {}
        if not isinstance(post, dict):
            continue
        title = str(post.get('subject') or post.get('title') or '')
        pid = str(post.get('post_id') or post.get('id') or '')
        if not TITLE.search(title) or not pid.isdigit():
            continue
        count += 1
        print(f'\nARTICLE: {title} | https://www.hoyolab.com/article/{pid}', flush=True)
        try:
            detail = get_json(DETAIL + '?' + urllib.parse.urlencode({'post_id': pid}))
            text = content_text(detail)
            print(f'Body text length: {len(text)}', flush=True)
            result, reason = parse_window(text)
            if result:
                start, end, hours = result
                print(f'PREVIEW ONLY: {start:%Y-%m-%d %H:%M} JST → {end:%Y-%m-%d %H:%M} JST (estimated, {hours}h)', flush=True)
            else:
                print(f'SKIPPED: {reason}; no inferred dates.', flush=True)
        except Exception as exc:
            print(f'WARNING: Detail fetch failed: {type(exc).__name__}: {str(exc)[:150]}', flush=True)
    print(f'\nChecked {count} maintenance notice(s). No files modified.', flush=True)

if __name__ == '__main__':
    main()
