"""Shared date contract; unknown ends are restricted to verified Endfield markers."""
import datetime as dt
import re
from urllib.parse import urlsplit


def is_unknown_end_marker(event):
    if not isinstance(event, dict) or 'end' not in event or event['end'] is not None:
        return False
    if event.get('game') != 'endfield' or event.get('source_status') != '公式開始日確認済み・終了日未定':
        return False
    if any(not isinstance(event.get(k), str) or not event[k].strip()
           for k in ('id', 'name', 'kind', 'start', 'end_note', 'official_url')):
        return False
    try:
        url = urlsplit(event['official_url'])
        return (url.scheme == 'https' and url.netloc == 'endfield.gryphline.com'
                and re.fullmatch(r'/ja-jp/news/[0-9]+', url.path) is not None
                and not url.query and not url.fragment and _date(event['start']) is not None)
    except ValueError:
        return False


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def valid_event_dates(event):
    if not isinstance(event, dict):
        return False
    start = _date(event.get('start'))
    if start is None:
        return False
    if is_unknown_end_marker(event):
        return True
    end = _date(event.get('end'))
    return end is not None and start <= end
