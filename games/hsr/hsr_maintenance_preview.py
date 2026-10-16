#!/usr/bin/env python3
"""Read-only preview of HSR maintenance announcements. Never edits events.json.

Scans links exposed by the official news homepage and checks a known official
update article as a parser smoke test. Discovery coverage is not guaranteed.
"""
import datetime as dt
import html
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

HOME = 'https://hsr.hoyoverse.com/ja-jp/home'
KNOWN = 'https://hsr.hoyoverse.com/en-us/news/166468'
MAX_BYTES = 2_000_000

class Extract(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if href:
                self.links.append(href)
    def handle_data(self, data):
        self.text.append(data)

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'GameEventCalendar/1.0'})
    with urllib.request.urlopen(req, timeout=20) as res:
        data = res.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Page too large')
    p = Extract()
    p.feed(data.decode('utf-8', 'replace'))
    return p

def parse_maintenance(text):
    # Require the official maintenance heading and an explicit UTC+8 timestamp.
    if not re.search(r'(?:Update Time|Maintenance Time|メンテナンス日時)', text, re.I):
        return None
    m = re.search(r'(20\d{2})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{2})(?::\d{2})?\s*\(?UTC\s*\+\s*8\)?', text, re.I)
    if not m:
        return None
    try:
        start = dt.datetime(*map(int, m.groups()), tzinfo=dt.timezone(dt.timedelta(hours=8)))
    except ValueError:
        return None
    return start.astimezone(dt.timezone(dt.timedelta(hours=9)))

def main():
    urls = [KNOWN]
    try:
        home = fetch(HOME)
        for link in home.links:
            url = urljoin(HOME, html.unescape(link))
            p = urlparse(url)
            if p.scheme == 'https' and p.hostname == 'hsr.hoyoverse.com' and re.fullmatch(r'/(?:ja-jp|en-us)/news/\d+', p.path):
                if url not in urls:
                    urls.append(url)
        print(f'Official homepage: {len(urls)-1} article link(s) found (not exhaustive).')
    except Exception as exc:
        print(f'WARNING: Homepage discovery unavailable: {exc}')
    for url in urls[:31]:
        try:
            page = fetch(url)
            text = re.sub(r'\s+', ' ', html.unescape(' '.join(page.text)))
            start = parse_maintenance(text)
            if start:
                print(f'CANDIDATE: {start:%Y-%m-%d %H:%M} JST | {url}')
                print('  End time not auto-confirmed; no calendar changes made.')
        except Exception as exc:
            print(f'WARNING: Skipped {url}: {exc}')
    print('Preview complete. No files modified. Discovery may miss JS-loaded news.')

if __name__ == '__main__':
    main()
