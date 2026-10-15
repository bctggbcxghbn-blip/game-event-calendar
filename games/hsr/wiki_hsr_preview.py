#!/usr/bin/env python3
"""Preview Japanese HSR wiki events; does not modify events.json."""
from html.parser import HTMLParser
from urllib.request import Request, urlopen
import re
import json

URL = 'https://wikiwiki.jp/star-rail/%E3%82%A4%E3%83%99%E3%83%B3%E3%83%88'

class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table_depth = 0
        self.row = None
        self.cell = None
        self.current_table = None
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            if self.table_depth == 0:
                self.current_table = []
            self.table_depth += 1
        elif self.table_depth and tag == 'tr':
            self.row = []
        elif self.table_depth and tag in ('td', 'th') and self.row is not None:
            self.cell = []
        elif self.cell is not None and tag == 'br':
            self.cell.append(' ')
    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(re.sub(r'\s+', ' ', ''.join(self.cell)).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.current_table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table_depth:
            self.table_depth -= 1
            if self.table_depth == 0:
                self.tables.append(self.current_table)
                self.current_table = None

def main():
    req = Request(URL, headers={'User-Agent': 'GameEventCalendar/1.0 (personal project)'})
    with urlopen(req, timeout=20) as response:
        html = response.read(2_000_000).decode('utf-8', 'replace')
    parser = Tables()
    parser.feed(html)
    rows = []
    for table in parser.tables:
        if not any('イベント名' in ' '.join(row) and '開催期間' in ' '.join(row) for row in table[:4]):
            continue
        for row in table:
            if len(row) < 2 or 'イベント名' in row[0]:
                continue
            period = row[-1]
            if not re.search(r'20\d{2}/\d{1,2}/\d{1,2}', period):
                continue
            rows.append({'name': row[0], 'period_text': period})
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f'Found {len(rows)} candidate rows. Dates are not yet normalized; review before import.')

if __name__ == '__main__':
    main()
