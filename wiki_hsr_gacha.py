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
    """Resolve rowspan/colspan into a rectangular grid."""
    grid = []
    pending = {}  # column -> (text, rows_remaining)
    for cells in rows:
        line = []
        col = 0
        def take_pending():
            nonlocal col
            while col in pending:
                value, left = pending[col]
                line.append(value)
                if left <= 1:
                    del pending[col]
                else:
                    pending[col] = (value, left - 1)
                col += 1
        for value, rowspan, colspan in cells:
            take_pending()
            for _ in range(colspan):
                line.append(value)
                if rowspan > 1:
                    pending[col] = (value, rowspan - 1)
                col += 1
        take_pending()
        # Rows may end with inherited cells from a later column.
        while pending and col <= max(pending):
            if col in pending:
                take_pending()
            else:
                line.append('')
                col += 1
        grid.append(line)
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
        # This table is the character/light-cone warp history, not an event list.
        heading = ' '.join(' '.join(r) for r in grid[:4])
        if 'イベント跳躍' not in heading or '光円錐' not in heading or '期間' not in heading:
            continue
        for row in grid:
            # Expected columns: version, period, warp name, 5* character,
            # 4* character, 5* light cone, 4* light cone.
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
                # Cell may contain multiple 5-star items separated by spaces.
                # Keep the exact wiki text rather than inventing a split.
                result.append((kind, name, start, end))
    return list(dict.fromkeys(result))


def main():
    request = Request(URL, headers={'User-Agent': 'GameEventCalendar/1.0 (personal project)'})
    with urlopen(request, timeout=20) as response:
        blob = response.read(2_000_001)
    if len(blob) > 2_000_000:
        raise ValueError('Wiki page exceeds 2 MB')
    candidates = collect(blob.decode('utf-8', 'replace'))
    if not candidates:
        raise ValueError('No warp rows found: Wiki table may have changed. events.json unchanged.')

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
