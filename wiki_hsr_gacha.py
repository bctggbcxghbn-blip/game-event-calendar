#!/usr/bin/env python3
"""Import HSR character and light-cone warp periods from Japanese Wiki.

Run after update_events.py and wiki_hsr_import.py. Preserve unrelated events.
A star marker is a Wiki hint, while older appearances establish reruns.
Uncertain classifications remain unconfirmed rather than being guessed.
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
            self.cell.append('\n')

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.cell is not None:
            self.cell.append('\n')
        elif tag in ('td', 'th') and self.cell is not None:
            value = '\n'.join(re.sub(r'\s+', ' ', part).strip() for part in ''.join(self.cell).split('\n') if part.strip())
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
    """Expand rowspan/colspan while respecting occupied columns."""
    grid = []
    carried = {}
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



def parse_period_times(value):
    """Read clock times explicitly printed next to the two period dates.

    Never infer a clock time from a version phase or maintenance notice.
    Returns (start_time, end_time) as HH:MM or None.
    """
    dates = list(re.finditer(r'(?:20\d{2}\s*/\s*)?\d{1,2}\s*/\s*\d{1,2}', value))
    if len(dates) < 2:
        return None, None

    times = []
