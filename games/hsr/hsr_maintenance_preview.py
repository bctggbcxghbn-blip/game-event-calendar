#!/usr/bin/env python3
"""Read-only preview: discover official HSR maintenance notices. Never edits files.

Discovery is best-effort; pages may require JavaScript or block automated requests.
A discovered link is NOT a verified maintenance window.
"""
import datetime as dt
import html
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

PAGES = [
    'https://sr.mihoyo.com/news',
    'https://hsr.hoyoverse.com/ja-jp/home',
]
KNOWN = 'https://hsr.hoyoverse.com/en-us/news/166468'
MAX_BYTES = 2_000_000
MAX_ARTICLES = 20

class Extract(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text = []
        self.title = ''
        self._title = False
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if href:
                self.links.append(href)
        if tag == 'title':
            self._title = True
    def handle_endtag(self, tag):
        if tag == 'title':
            self._title = False
    def handle_data(self, data):
        self.text.append(data)
        if self._title:
            self.title += data

def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; GameEventCalendarPreview/1.0)',
        'Accept-Language': 'zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7',
    })
    with urllib.request.urlopen(req, timeout=20) as res:
        data = res.read(MAX_BYTES + 1)
        final_url = res.geturl()
    if len(data) > MAX_BYTES:
        raise ValueError('Page too large')
    raw = data.decode('utf-8', 'replace')
    parser = Extract()
    parser.feed(raw)
    return parser, raw, final_url

def is_official_article(url):
    p = urlparse(url)
    if p.scheme != 'https' or p.hostname not in {'sr.mihoyo.com', 'hsr.hoyoverse.com'}:
        return False
    return bool(re.search(r'/(?:news|article|detail)/[^/?#]+', p.path, re.I))

def find_links(base, parser, raw):
    # Include links serialized in JavaScript state, even when <a> tags are absent.
    candidates = list(parser.links)
    candidates.extend(re.findall(r'https?(?:\\/\\/|://)[^\s"\'<>]+', raw))
    candidates.extend(re.findall(r'["\']((?:/news/|/article/|/detail/)[^"\'<>\s]+)["\']', raw))
    found = []
    for candidate in candidates:
        candidate = html.unescape(candidate).replace('\\/', '/')
        candidate = candidate.rstrip('.,;)]}')
        url = urljoin(base, candidate)
        if is_official_article(url):
            normalized = url.split('#', 1)[0].split('?', 1)[0]
            if normalized not in found:
                found.append(normalized)
    return found

def parse_maintenance(text):
    # Conservative parser: only accept a maintenance heading and explicit UTC+8 time.
    if not re.search(r'(?:Update Time|Maintenance Time|メンテナンス日時|维护时间|停服维护)', text, re.I):
        return None
    m = re.search(r'(20\d{2})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{2})(?::\d{2})?\s*\(?\s*(?:UTC|GMT)\s*\+\s*8\s*\)?', text, re.I)
    if not m:
        return None
    try:
        start = dt.datetime(*map(int, m.groups()), tzinfo=dt.timezone(dt.timedelta(hours=8)))
    except ValueError:
        return None
    return start.astimezone(dt.timezone(dt.timedelta(hours=9)))

def main():
    urls = []
    for page_url in PAGES:
        try:
            page, raw, final_url = fetch(page_url)
            found = find_links(final_url, page, raw)
            print(f'SOURCE: {page_url}')
            print(f'  Final URL: {final_url}')
            print(f'  Title: {page.title.strip()[:100] or "(none)"}')
            print(f'  HTML size: {len(raw)} chars; HTML links: {len(page.links)}; official article links: {len(found)}')
            for url in found[:10]:
                print(f'  ARTICLE: {url}')
            urls.extend(url for url in found if url not in urls)
        except Exception as exc:
            print(f'WARNING: Cannot read {page_url}: {type(exc).__name__}: {exc}')
    # A known article is a parser smoke test, not a discovery result.
    check_urls = urls[:MAX_ARTICLES]
    if KNOWN not in check_urls:
        check_urls.append(KNOWN)
    print(f'Discovered {len(urls)} unique official article links; checking up to {len(check_urls)} pages.')
    for url in check_urls:
        try:
            page, _, _ = fetch(url)
            text = re.sub(r'\s+', ' ', html.unescape(' '.join(page.text)))
            heading = bool(re.search(r'(?:更新维护|维护预告|Maintenance|メンテナンス)', text, re.I))
            start = parse_maintenance(text)
            if start:
                print(f'POSSIBLE TIME: {start:%Y-%m-%d %H:%M} JST | {url}')
                print('  Needs manual verification; end time not verified.')
            elif heading:
                print(f'POSSIBLE NOTICE (no verified timestamp): {url}')
        except Exception as exc:
            print(f'WARNING: Cannot read article {url}: {type(exc).__name__}: {exc}')
    print('Preview complete. No files modified. Zero results do not prove no announcements exist.')

if __name__ == '__main__':
    main()
