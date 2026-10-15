#!/usr/bin/env python3
"""Read-only HSR announcement event-period candidate extractor.

Only reports explicit date ranges. Does not alter events.json or infer server timezone.
Publisher identity check is provisional and should be independently validated.
"""
import datetime as dt
import re
import json
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://bbs-api-os.hoyolab.com/community/post/wapi/"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://www.hoyolab.com/"}
EXPECTED_UID = "172534910"
EXPECTED_CERT = "HonkaiSR Official"

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def handle_starttag(self, tag, attrs):
        if tag in ('br', 'p', 'div', 'li'):
            self.parts.append('\n')

def fetch(endpoint, params):
    url = BASE + endpoint + '?' + urlencode(params)
    with urlopen(Request(url, headers=HEADERS), timeout=20) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError('API response too large')
    result = json.loads(raw)
    if result.get('retcode') != 0:
        raise ValueError('API error: ' + str(result.get('message')))
    return result.get('data') or {}

def as_text(post):
    chunks = []
    structured = post.get('structured_content')
    if structured:
        try:
            blocks = json.loads(structured) if isinstance(structured, str) else structured
            if isinstance(blocks, list):
                chunks.extend(str(block.get('insert', '')) for block in blocks if isinstance(block, dict) and isinstance(block.get('insert'), str))
        except (ValueError, TypeError):
            pass
    if not chunks:
        parser = PlainText()
        parser.feed(str(post.get('content') or ''))
        chunks.append(''.join(parser.parts))
    return unescape('\n'.join(chunks))



MAX_ARTICLES = 20
DATE = r'20\d{2}[/-]\d{1,2}[/-]\d{1,2}'
CLOCK = r'\d{1,2}:\d{2}'
START = rf'(?:(?:after\s+the\s+(?:Version\s+[\d.]+\s+)?update\s+on\s+{DATE})|(?:{DATE}\s+{CLOCK}))'
# Require explicit date/time for the ending, and a nearby separator.
RANGE = re.compile(rf'(?P<start>{START})(?:\s*\([^)]{{0,40}}\))?\s*[–—-]\s*(?P<end>{DATE}\s+{CLOCK})\s*(?P<tz>\((?:UTC\s*\+\s*8|server\s+time)\))?', re.I)
DATE_ONLY_AFTER = re.compile(rf'after\s+the\s+(?:Version\s+[\d.]+\s+)?update\s+on\s+(?P<date>{DATE})', re.I)

def candidate(m, body):
    raw_start = m.group('start').strip()
    end = m.group('end')
    tz = (m.group('tz') or '').lower()
    context = ' '.join(body[max(0, m.start()-110):min(len(body), m.end()+100)].split())
    after_update = raw_start.lower().startswith('after')
    if after_update:
        date_match = DATE_ONLY_AFTER.search(raw_start)
        if not date_match:
            return None
        start_date = date_match.group('date').replace('/', '-')
        start_clock = None
    else:
        start_date, start_clock = raw_start.split()
        start_date = start_date.replace('/', '-')
    end_date, end_clock = end.split()
    end_date = end_date.replace('/', '-')
    try:
        begin = dt.date.fromisoformat(start_date)
        finish = dt.date.fromisoformat(end_date)
        if finish < begin or (finish - begin).days > 120:
            return None
    except ValueError:
        return None
    # Do not silently convert server time: Asia/Europe/America may differ.
    if 'utc' in tz:
        zone = 'UTC+8'
    elif 'server' in tz:
        zone = 'server time (region unknown)'
    else:
        zone = 'UNSPECIFIED'
    return {'start': start_date, 'start_time': start_clock,
            'start_label': 'アップデート後' if after_update else None,
            'end': end_date, 'end_time': end_clock,
            'timezone': zone, 'context': context[:230]}

def main():
    ids = {}
    for category in (1, 2, 3):
        try:
            data = fetch('getNewsList', {'gids': 6, 'type': category, 'page_size': 20})
            for entry in data.get('list') or []:
                post = entry.get('post') or {}
                pid = str(post.get('post_id') or '')
                if pid.isdigit():
                    ids.setdefault(pid, str(post.get('subject') or 'Untitled'))
        except Exception as exc:
            print(f'WARNING: list category {category}: {exc}')
    print(f'Found {len(ids)} article IDs; inspecting up to {MAX_ARTICLES}.')
    total = 0
    for pid, fallback in list(ids.items())[:MAX_ARTICLES]:
        try:
            data = fetch('getPostFull', {'post_id': pid})
            wrapper = data.get('post') or {}
            post = wrapper.get('post') or {}
            user = wrapper.get('user') or {}
            cert = user.get('certification') or {}
            if not (str(user.get('uid')) == EXPECTED_UID and
                    user.get('nickname') == 'Honkai: Star Rail' and
                    isinstance(cert, dict) and cert.get('desc') == EXPECTED_CERT):
                print(f'SKIP: publisher mismatch for {pid}')
                continue
            body = as_text(post)
            candidates = []
            seen = set()
            for match in RANGE.finditer(body):
                c = candidate(match, body)
                if c:
                    key = (c['start'], c['start_time'], c['end'], c['end_time'], c['timezone'])
                    if key not in seen:
                        seen.add(key)
                        candidates.append(c)
            if not candidates:
                continue
            print(f'\nARTICLE: {post.get("subject") or fallback}\nURL: https://www.hoyolab.com/article/{pid}')
            for c in candidates[:12]:
                total += 1
                print(f'  CANDIDATE: {c["start"]} {c["start_label"] or c["start_time"]} -> {c["end"]} {c["end_time"]} [{c["timezone"]}]')
                print(f'    CONTEXT: {c["context"]}')
            if len(candidates) > 12:
                print(f'  ... {len(candidates)-12} additional candidates omitted')
        except Exception as exc:
            print(f'WARNING: article {pid}: {type(exc).__name__}: {exc}')
    print(f'\nDone: {total} date-range candidates. events.json unchanged.')
    print('Candidates are NOT events: headings, timezone and game-server region require review.')

if __name__ == '__main__':
    main()
