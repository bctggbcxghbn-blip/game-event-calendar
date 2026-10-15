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

ROOT = pathlib.Path(__file__).resolve().parents[2]
URL = 'https://wikiwiki.jp/star-rail/%E3%82%A4%E3%83%99%E3%83%B3%E3%83%88'
DATE = r'(20\d{2})/(\d{1,2})/(\d{1,2})'
PERIOD = re.compile(r'^\s*' + DATE + r'(?:\s+([01]?\d|2[0-3]):([0-5]\d))?\s*[〜～~–—－-]\s*(?:' + DATE + r'|(\d{1,2})/(\d{1,2}))(?:\s+([01]?\d|2[0-3]):([0-5]\d))?\s*$')

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
    if m.group(6):
        b = dt.date(*map(int, m.group(6, 7, 8)))
    else:
        month, day = int(m.group(9)), int(m.group(10))
        year = a.year + (month, day).__lt__((a.month, a.day))
        b = dt.date(year, month, day)
    if b < a or (b - a).days > 180:
        return None
    return (a.isoformat(), b.isoformat(),
            f'{int(m.group(4)):02d}:{m.group(5)}' if m.group(4) else None,
            f'{int(m.group(11)):02d}:{m.group(12)}' if m.group(11) else None)

def normalize(text):
    return re.sub(r'[\s:：・「」『』\-–—!！?？]+', '', text).casefold()

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
    inserted = updated = skipped = timed = 0
    seen = set()
    for name, start, end, start_time, end_time in candidates:
        key = (normalize(name), start, end)
        if key in seen or dt.date.fromisoformat(end) < cutoff:
            skipped += 1
            continue
        seen.add(key)
        candidate = {'game': 'hsr', 'name': name, 'start': start, 'end': end}
        clocks = {k: v for k, v in (('start_time', start_time), ('end_time', end_time)) if v}
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
                for field, value in clocks.items():
                    if row.get(field) != value:
                        row[field] = value
                        timed += 1
            continue
        uid = hashlib.sha256(('hsr|wiki|' + name + '|' + start).encode()).hexdigest()[:20]
        entry = {
            'id': 'wiki-hsr-' + uid, 'game': 'hsr', 'name': name,
            'start': start, 'end': end, 'kind': 'イベント',
            'url': URL, 'source_status': '日本語Wiki・日付確認済み'
        }
        entry.update(clocks)
        if clocks:
            timed += 1
        existing.append(entry)
        inserted += 1
    existing.sort(key=lambda row: (row.get('start', ''), row.get('game', ''), row.get('name', '')))

    # Confirmed English/Japanese aliases: merge only known identical events.
    confirmed_pairs = {
        'Interastral Peace Gala: One Take': 'スターピースフェスティバル：ワンカット',
    }

    for english, japanese in confirmed_pairs.items():
        api_rows = [
            row for row in existing
            if row.get('game') == 'hsr'
            and (row.get('original_name') or row.get('name')) == english
        ]
        wiki_rows = [
            row for row in existing
            if row.get('game') == 'hsr'
            and normalize(row.get('name', '')) == normalize(japanese)
            and str(row.get('id', '')).startswith('wiki-hsr-')
        ]

        for api_row in api_rows:
            duplicates = [
                row for row in wiki_rows
                if overlaps(api_row, row)
            ]
            if duplicates:
                api_row['original_name'] = english
                api_row['name'] = japanese
                for duplicate in duplicates:
                    if duplicate in existing:
                        existing.remove(duplicate)
                print(f'Merged duplicate: {english} -> {japanese}')

    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Wiki: {len(candidates)} dated candidates; {inserted} added, {updated} renamed, {skipped} old/duplicate skipped.')
    print(f'Wiki: {timed} event clock fields/entries confirmed from explicit period text.')
    print('NOTE: Challenge times not shown in the event table remain unconfirmed.')
    print('NOTE: Unmatched English API entries remain; inspect calendar for semantic duplicates.')

# Official HoYoverse announcements verified against the dated periods shown in
# the Japanese announcements. Times there are server times (Asia server UTC+8).
# This is a verified-source snapshot, not a live announcement scraper.
OFFICIAL_PERIODS = [
    # category, start date, end date, start server clock, end server clock, source
    ('虚構叙事', '2026-09-14', '2026-10-19', '04:00', '03:59',
     'https://hsr.hoyoverse.com/ja-jp/news/165767'),
    ('末日の幻影', '2026-10-05', '2026-11-16', '04:00', '03:59',
     'https://hsr.hoyoverse.com/ja-jp/news/166468'),
    ('虚構叙事', '2026-10-19', '2026-11-30', '04:00', '03:59',
     'https://hsr.hoyoverse.com/ja-jp/news/166468'),
    ('混沌の記憶', '2026-11-02', '2026-12-14', '04:00', '03:59',
     'https://hsr.hoyoverse.com/ja-jp/news/166468'),
    # The earlier Memory of Chaos start clock was not visible in the evidence.
    ('混沌の記憶', '2026-09-28', '2026-11-02', None, '03:59',
     'https://hsr.hoyoverse.com/ja-jp/news/166468'),
]

def server_clock_to_jst(clock):
    """Asia-server UTC+8 clock to JST UTC+9; return (clock, day shift)."""
    if clock is None:
        return None, 0
    hour, minute = map(int, clock.split(':'))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError('Invalid clock: ' + clock)
    total = hour * 60 + minute + 60
    return f'{(total // 60) % 24:02d}:{total % 60:02d}', total // 1440

def enrich_challenge_times():
    path = ROOT / 'events.json'
    events = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise ValueError('events.json must be a list')
    confirmed = {}
    for category, start, end, st, et, url in OFFICIAL_PERIODS:
        key = (category, start, end)
        if key in confirmed:
            raise ValueError('Duplicate official period: ' + str(key))
        confirmed[key] = (st, et, url)
    changed = 0
    unmatched = 0
    for event in events:
        if not isinstance(event, dict) or event.get('game') != 'hsr':
            continue
        name = str(event.get('name', ''))
        original = str(event.get('original_name', ''))
        categories = {
            '虚構叙事': ('虚構叙事' in name or 'Pure Fiction' in original),
            '混沌の記憶': ('混沌の記憶' in name or 'Memory of Chaos' in original),
            '末日の幻影': ('末日の幻影' in name or 'Apocalyptic Shadow' in original),
        }
        matches = [cat for cat, matched in categories.items() if matched]
        if len(matches) != 1:
            continue
        key = (matches[0], event.get('start'), event.get('end'))
        source = confirmed.get(key)
        if not source:
            unmatched += 1
            continue
        st, et, url = source
        new = {}
        for prefix, server_time, date_key in (
            ('start', st, 'start'), ('end', et, 'end')
        ):
            if server_time is None:
                continue
            jst, shift = server_clock_to_jst(server_time)
            original_date = dt.date.fromisoformat(event[date_key])
            shifted_date = (original_date + dt.timedelta(days=shift)).isoformat()
            # Preserve the API's date; never silently move an event's date.
            if shifted_date != event[date_key]:
                print(f'WARNING: JST date shift for {name}; {prefix} skipped')
                continue
            field = prefix + '_time'
            if event.get(field) not in (None, jst):
                print(f'WARNING: conflicting {field} for {name}; skipped')
                continue
            new[field] = jst
        if not new:
            continue
        new['time_zone'] = 'Asia/Tokyo'
        new['time_source_url'] = url
        if any(event.get(k) != v for k, v in new.items()):
            event.update(new)
            changed += 1
    if changed:
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'HSR official challenge clocks: {changed} event(s) updated; '
          f'{unmatched} unmatched challenge rows unchanged.')
    print('NOTE: Official period snapshot from announcements; future seasons require new verified entries.')

if __name__ == '__main__':
    main()
    enrich_challenge_times()

