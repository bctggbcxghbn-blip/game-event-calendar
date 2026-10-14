#!/usr/bin/env python3
"""Import HSR character and light-cone warp periods from Japanese Wiki.

Run after update_events.py and wiki_hsr_import.py. Fail safely if the Wiki
structure changes; never delete unrelated calendar events.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
from html.parser import HTMLParser
from urllib.request import Request, urlopen

ROOT = pathlib.Path(__file__).resolve().parent
URL = 'https://wikiwiki.jp/star-rail/%E8%B7%B3%E8%BA%8D'
JST = dt.timezone(dt.timedelta(hours=9))
DATE = re.compile(r'(20\d{2})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})')


class WikiTables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.depth = 0
        self.table = None
        self.row = None
        self.cell = None
        self.span = 1
        self.colspan = 1
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            if self.depth == 0:
                self.table = []
            self.depth += 1
        elif self.depth == 1 and tag == 'tr':
            self.row = []
        elif self.depth == 1 and tag in ('td', 'th') and self.row is not None:
            self.cell = []
            self.span = min(100, max(1, int(attrs.get('rowspan', '1') or '1')))
            self.colspan = min(20, max(1, int(attrs.get('colspan', '1') or '1')))
        elif tag == 'br' and self.cell is not None:
            self.cell.append(' ')

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            value = re.sub(r'\s+', ' ', ''.join(self.cell)).strip()
            self.row.append((value, self.span, self.colspan))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            if self.table is not None:
                self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.depth:
            self.depth -= 1
            if self.depth == 0:
                self.tables.append(self.table)
                self.table = None


def expand_table(rows):
    """Expand rowspan/colspan while respecting occupied columns.

    A carried-over cell can be in the *middle* of a new row. Therefore,
    appending the next explicit cell directly after the previous one shifts
    all later columns and can turn version labels into gacha names.
    """
    grid = []
    carried = {}  # column -> (text, remaining future rows)
    for cells in rows:
        occupied = {col: text for col, (text, _) in carried.items()}
        future = {}
        for col, (text, remaining) in carried.items():
            if remaining > 1:
                future[col] = (text, remaining - 1)
        col = 0
        for value, rowspan, colspan in cells:
            while any((col + offset) in occupied for offset in range(colspan)):
                col += 1
            for offset in range(colspan):
                dest = col + offset
                if dest in occupied:
                    raise ValueError('Overlapping Wiki table cells')
                occupied[dest] = value
                if rowspan > 1:
                    future[dest] = (value, rowspan - 1)
            col += colspan
        width = max(occupied, default=-1) + 1
        grid.append([occupied.get(i, '') for i in range(width)])
        carried = future
    return grid


def parse_period(value):
    found = DATE.findall(value)
    if not found:
        return None
    start = dt.date(*map(int, found[0]))
    if len(found) >= 2:
        end = dt.date(*map(int, found[1]))
    else:
        tail = value[DATE.search(value).end():]
        m = re.search(r'[〜～~–—－-]\s*(\d{1,2})\s*/\s*(\d{1,2})', tail)
        if not m:
            return None
        month, day = map(int, m.groups())
        end = dt.date(start.year + ((month, day) < (start.month, start.day)), month, day)
    if end < start or (end - start).days > 90:
        return None
    return start.isoformat(), end.isoformat()


def clean(text):
    return re.sub(r'\s+', ' ', text).strip().replace('☆', '').replace('★', '').strip()


def collect(html):
    parser = WikiTables()
    parser.feed(html)
    result = []
    for raw in parser.tables:
        grid = expand_table(raw)
        heading = ' '.join(' '.join(r) for r in grid[:4])
        if 'イベント跳躍' not in heading or '光円錐' not in heading or '期間' not in heading:
            continue
        for row in grid:
            # Version | period | warp | 5-star character | 4-star character |
            # 5-star light cone | 4-star light cone
            if len(row) < 7:
                continue
            period = parse_period(row[1])
            if not period:
                continue
            start, end = period
            for kind, name in [('ガチャ（新規・復刻未確認）', row[3]), ('武器・装備ガチャ', row[5])]:
                name = clean(name)
                if not name or name in ('PUなし', '-', 'なし'):
                    continue
                # Safety: do not import obvious version/phase labels as items.
                if re.search(r'Ver\.?\s*\d+\.\d+|\d+\.\d+\s*(?:前|後)半?', name, re.I):
                    continue
                result.append((kind, name, start, end))
    return list(dict.fromkeys(result))


def main():
    request = Request(URL, headers={'User-Agent': 'GameEventCalendar/1.0 (personal project)'})
    with urlopen(request, timeout=20) as response:
        blob = response.read(2_000_001)
    if len(blob) > 2_000_000:
        raise ValueError('Wiki page exceeds 2 MB')
    candidates = collect(blob.decode('utf-8', 'replace'))
    if len(candidates) < 4:
        raise ValueError('Too few warp entries: Wiki table may have changed. events.json unchanged.')

    path = ROOT / 'events.json'
    events = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise ValueError('events.json must be a list')
    cutoff = dt.datetime.now(JST).date() - dt.timedelta(days=14)
    # Only replace previously imported Wiki gacha when parsing succeeds.
    events = [e for e in events if not str(e.get('id', '')).startswith('wiki-hsr-gacha-')]
    added = 0
    for kind, name, start, end in candidates:
        if dt.date.fromisoformat(end) < cutoff:
            continue
        uid = hashlib.sha256(f'hsr|gacha|{kind}|{name}|{start}'.encode()).hexdigest()[:20]
        events.append({
            'id': 'wiki-hsr-gacha-' + uid,
            'game': 'hsr', 'name': name, 'start': start, 'end': end,
            'kind': kind, 'url': URL,
            'source_status': '日本語Wiki・ガチャ日付確認済み',
        })
        added += 1
    events.sort(key=lambda e: (e.get('start', ''), e.get('game', ''), e.get('name', '')))
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'HSR gacha: {len(candidates)} rows found, {added} current/upcoming entries added.')


if __name__ == '__main__':
    main()
