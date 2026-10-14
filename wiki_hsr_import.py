#!/usr/bin/env python3
"""Import explicitly dated Japanese HSR wiki events into events.json.

Run after update_events.py. Conservative duplicate detection: reviewed translations
and exact Japanese names, with overlapping dates. Ambiguous matches are not guessed.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
from html.parser import HTMLParser
from urllib.request import Request, urlopen

ROOT = pathlib.Path(__file__).resolve().parent
URL = 'https://wikiwiki.jp/star-rail/%E3%82%A4%E3%83%99%E3%83%B3%E3%83%88'
DATE = r'(20\d{2})/(\d{1,2})/(\d{1,2})'
PERIOD = re.compile(r'^\s*' + DATE + r'\s*[〜～~–—－-]\s*(?:' + DATE + r'|(\d{1,2})/(\d{1,2}))\s*$')

class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.depth = 0
        self.table = None
        self.row = None
        self.cell = None
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            if self.depth == 0:
                self.table = []
            self.depth += 1
        elif self.depth and tag == 'tr':
            self.row = []
        elif self.depth and tag in ('td', 'th') and self.row is not None:
            self.cell = []
        elif tag == 'br' and self.cell is not None:
            self.cell.append(' ')
    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(re.sub(r'\s+', ' ', ''.join(self.cell)).strip())
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

def parse_period(text):
    # Reject uncertain text, e.g. 'アップデート後', 'Ver.4.6終了まで'.
    m = PERIOD.fullmatch(text.strip())
    if not m:
        return None
    a = dt.date(*map(int, m.group(1, 2, 3)))
    if m.group(4):
        b = dt.date(*map(int, m.group(4, 5, 6)))
    else:
        month, day = int(m.group(7)), int(m.group(8))
        year = a.year + (month, day).__lt__((a.month, a.day))
        b = dt.date(year, month, day)
    if b < a or (b - a).days > 180:
        return None
    return a.isoformat(), b.isoformat()

def normalize(text):
    return re.sub(r'[\s:：・「」『』\-–—!！]+', '', text).casefold()

def overlaps(a, b):
    return a['start'] <= b['end'] and b['start'] <= a['end']

def main():
    req = Request(URL, headers={'User-Agent': 'GameEventCalendar/1.0 (personal project)'})
    with urlopen(req, timeout=20) as resp:
        blob = resp.read(2_000_001)
    if len(blob) > 2_000_000:
        raise ValueError('Wiki page exceeds 2 MB')
    parser = Tables()
    parser.feed(blob.decode('utf-8', 'replace'))
    candidates = []
    for table in parser.tables:
        if not any('イベント名' in ' '.join(row) and '開催期間' in ' '.join(row) for row in table[:4]):
            continue
        for row in table:
            if len(row) < 2 or 'イベント名' in row[0]:
                continue
            try:
                dates = parse_period(row[-1])
            except ValueError:
                dates = None
            if dates and row[0].strip():
                candidates.append((row[0].strip(), *dates))

    path = ROOT / 'events.json'
    existing = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(existing, list):
        raise ValueError('events.json must be a list')
    labels_path = ROOT / 'labels_ja.json'
    labels = json.loads(labels_path.read_text(encoding='utf-8')) if labels_path.exists() else {}
    translations = labels.get('hsr', {}) if isinstance(labels, dict) else {}
    aliases = {}
    for english, data in translations.items():
        if isinstance(data, dict) and isinstance(data.get('name'), str):
            aliases[english] = data['name']

    # Avoid bringing in stale historical events from the entire Wiki archive.
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    cutoff = today - dt.timedelta(days=14)
    inserted = updated = skipped = 0
    seen = set()
    for name, start, end in candidates:
        key = (normalize(name), start, end)
        if key in seen or dt.date.fromisoformat(end) < cutoff:
            skipped += 1
            continue
        seen.add(key)
        candidate = {'game': 'hsr', 'name': name, 'start': start, 'end': end}
        matching = []
        for row in existing:
            if not isinstance(row, dict) or row.get('game') != 'hsr':
                continue
            original = row.get('original_name', row.get('name', ''))
            translated = aliases.get(original, row.get('name', ''))
            # Full-name exact match only. Do not merge unrelated events sharing dates.
            if normalize(translated) == normalize(name) and overlaps(candidate, row):
                matching.append(row)
        if matching:
            for row in matching:
                if row['name'] != name:
                    row.setdefault('original_name', row['name'])
                    row['name'] = name
                    updated += 1
            continue
        uid = hashlib.sha256(('hsr|wiki|' + name + '|' + start).encode()).hexdigest()[:20]
        existing.append({
            'id': 'wiki-hsr-' + uid, 'game': 'hsr', 'name': name,
            'start': start, 'end': end, 'kind': 'イベント',
            'url': URL, 'source_status': '日本語Wiki・日付確認済み'
        })
        inserted += 1
    existing.sort(key=lambda row: (row.get('start', ''), row.get('game', ''), row.get('name', '')))
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Wiki: {len(candidates)} dated candidates; {inserted} added, {updated} renamed, {skipped} old/duplicate skipped.')
    print('NOTE: Unmatched English API entries remain; inspect calendar for semantic duplicates.')

if __name__ == '__main__':
    main()
