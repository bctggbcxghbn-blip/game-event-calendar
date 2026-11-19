"""Conservative discovery of current versions from official Japanese pages.

The parser accepts only pages from the allow-listed official domains which
contain an explicit version, Japanese/JP context, and an explicit effective
date. It returns PR2 candidate snapshots and never writes calendar data.
"""
import datetime as dt
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from tools.update_versions import GAMES

DOMAIN = {
    'genshin': {'genshin.hoyoverse.com', 'www.hoyolab.com'},
    'wuwa': {'wutheringwaves.kurogames.com'},
    'hsr': {'hsr.hoyoverse.com', 'www.hoyolab.com'},
    'zzz': {'zenless.hoyoverse.com', 'www.hoyolab.com'},
    'nte': {'nte.perfectworld.com'},
    'arknights': {'arknights.jp', 'arknights.wikiru.jp'},
    'endfield': {'endfield.gryphline.com'},
}
VERSION_RE = re.compile(r'(?i)\b(?:ver(?:sion)?\.?|バージョン)\s*([0-9]+(?:\.[0-9]+)+)')
DATE_RE = re.compile(r'(20\d{2})[年/.-](\d{1,2})[月/.-](\d{1,2})')


def official_domain(game, url):
    return urlparse(url).scheme == 'https' and urlparse(url).hostname in DOMAIN.get(game, set())


def discover_html(game, html, url, checked_at, today=None):
    """Extract one verified candidate from an official JP article snapshot."""
    if game not in GAMES or game == 'arknights' or not official_domain(game, url):
        return None
    text = re.sub(r'<[^>]+>', ' ', html or '')
    if not re.search(r'(?i)(日本|日本語|\bJP\b|ja-jp|/jp/)', text + ' ' + url):
        return None
    version = VERSION_RE.search(text)
    date = DATE_RE.search(text)
    if not version or not date:
        return None
    effective = f'{date.group(1)}-{int(date.group(2)):02d}-{int(date.group(3)):02d}'
    if today is not None and dt.date.fromisoformat(effective) > today:
        return None
    return {'game': game, 'version': version.group(1), 'status': 'official',
            'official_url': url, 'checked_at': checked_at,
            'effective_from': effective, 'expires_at': None, 'region': 'JP'}


def fetch_candidate(game, url, checked_at, timeout=15, today=None):
    if not official_domain(game, url):
        return None
    try:
        request = Request(url, headers={'User-Agent': 'GameEventCalendar/1.0'})
        html = urlopen(request, timeout=timeout).read().decode('utf-8', 'replace')
    except OSError:
        return None
    return discover_html(game, html, url, checked_at, today=today)
