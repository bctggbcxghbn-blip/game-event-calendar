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
    for index in range(2):
        after = value[dates[index].end():dates[index + 1].start() if index + 1 < len(dates) else len(value)]
        # Time must follow its date, before the next date or period separator.
        after = re.split(r'[〜～~–—－]|\s+-\s+', after, maxsplit=1)[0]
        match = re.search(r'(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)', after)
        times.append(f'{int(match.group(1)):02d}:{match.group(2)}' if match else None)
    return tuple(times)



class WikiText(HTMLParser):
    """Extract readable page text, preserving block boundaries."""
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def handle_starttag(self, tag, attrs):
        if tag in ('br', 'p', 'div', 'li', 'tr', 'h2', 'h3', 'h4'):
            self.parts.append('\n')


def heading_times(html):
    """Index explicit date/time pairs from Wiki's '期間:' announcement lines.

    The table often has only dates, whereas the section above it includes
    '期間: Ver.Xアップデート後 - 2026/10/21 12:59'.
    """
    parser = WikiText()
    parser.feed(html)
    text = ''.join(parser.parts)
    result = {}
    for match in re.finditer(r'期間\s*[:：]\s*([^\n]{0,180})', text):
        line = match.group(1)
        if not ('イベント跳躍' in text[max(0, match.start()-350):match.start()] or 'アップデート' in line or len(DATE.findall(line)) >= 2):
            continue
        stamps = []
        for d in DATE.finditer(line):
            tail = line[d.end():]
            tm = re.match(r'\s+([01]?\d|2[0-3]):([0-5]\d)', tail)
            if tm:
                date = dt.date(*map(int, d.groups())).isoformat()
                stamps.append((date, f'{int(tm.group(1)):02d}:{tm.group(2)}'))
        if not stamps:
            continue
        # The section has one date -> it is the ending timestamp.
        # Two dates -> beginning and ending timestamps.
        if len(stamps) == 1:
            result.setdefault(('end', stamps[0][0]), stamps[0][1])
        else:
            result.setdefault(('start', stamps[0][0]), stamps[0][1])
            result.setdefault(('end', stamps[-1][0]), stamps[-1][1])
    return result


def clean(text):
    return re.sub(r'\s+', ' ', text).strip().replace('☆', '').replace('★', '').strip()


def split_items(cell):
    """Return (name, has_star) for each Wiki link/line."""
    items = []
    for part in cell.split('\n'):
        starred = '☆' in part or '★' in part
        name = clean(part)
        name = re.sub(r'(?:Ver\.?\s*)?\d+\.\d+\s*(?:前|後)半?$', '', name, flags=re.I).strip()
        if not name or name in ('PUなし', '-', 'なし'):
            continue
        if re.fullmatch(r'(?:Ver\.?\s*)?\d+\.\d+\s*(?:前|後)半?', name, re.I):
            continue
        if name not in [x[0] for x in items]:
            items.append((name, starred))
    return items


def collect(html):
    clock_index = heading_times(html)
    parser = WikiTables()
    parser.feed(html)
    result = []
    for raw in parser.tables:
        grid = expand_table(raw)
        heading = ' '.join(' '.join(r) for r in grid[:4])
        if 'イベント跳躍' not in heading or '光円錐' not in heading or '期間' not in heading:
            continue
        for row in grid:
            if len(row) < 7:
                continue
            period = parse_period(row[1])
            if not period:
                continue
            start, end = period
            table_start_time, table_end_time = parse_period_times(row[1])
            start_time = table_start_time or clock_index.get(('start', start))
            end_time = table_end_time or clock_index.get(('end', end))
            for item_type, cell in [('character', row[3]), ('lightcone', row[5])]:
                for name, starred in split_items(cell):
                    result.append((item_type, name, start, end, starred, start_time, end_time))
    return list(dict.fromkeys(result))


def classify(candidates):
    """Determine reruns from earlier entries; a star suggests debut.

    Do not assume an unstarred item is a rerun without earlier evidence.
    """
    first_seen = {}
    for item_type, name, start, _, _, _, _ in candidates:
        key = (item_type, name)
        if key not in first_seen or start < first_seen[key]:
            first_seen[key] = start
    for item_type, name, start, end, starred, start_time, end_time in candidates:
        if item_type == 'lightcone':
            kind = '武器・装備ガチャ'
        elif first_seen[(item_type, name)] < start:
            kind = '復刻キャラ'
        elif starred:
            kind = '新キャラ'
        else:
            kind = 'ガチャ（新規・復刻未確認）'
        yield kind, name, start, end, start_time, end_time


def main():
    request = Request(URL, headers={'User-Agent': 'GameEventCalendar/1.0 (personal project)'})
    with urlopen(request, timeout=20) as response:
        blob = response.read(2_000_001)
    if len(blob) > 2_000_000:
