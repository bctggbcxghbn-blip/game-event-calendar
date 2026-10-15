#!/usr/bin/env python3
"""Read-only HSR official news discovery diagnostic.

Run before the existing hsr_official_import.py. This tool NEVER modifies events.json.
It checks whether article URLs are discoverable in the official news page HTML.
"""
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

PAGES = [
    'https://hsr.hoyoverse.com/ja-jp/news',
    'https://hsr.hoyoverse.com/ja-jp/home',
]
ARTICLE = re.compile(r'/news/(\d{5,9})(?:[/?#]|$)')

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        href = dict(attrs).get('href', '')
        if href:
            self.links.append(href)

def get(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; GameEventCalendar/1.0)'})
    with urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise ValueError(f'HTTP {response.status}')
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError('Page larger than 2MB')
    return body.decode('utf-8', 'replace')

def main():
    found = set()
    for page in PAGES:
        try:
            html = get(page)
            parser = Links()
            parser.feed(html)
            urls = [urljoin(page, href) for href in parser.links]
            # Also inspect embedded link strings, for sites that hydrate via JSON.
            urls += [f'https://hsr.hoyoverse.com/ja-jp/news/{x}' for x in re.findall(r'(?<!\d)/news/(\d{5,9})(?!\d)', html)]
            accepted = 0
            for url in urls:
                parsed = urlparse(url)
                if parsed.hostname != 'hsr.hoyoverse.com' or not ARTICLE.search(parsed.path):
                    continue
                article_id = ARTICLE.search(parsed.path).group(1)
                found.add(f'https://hsr.hoyoverse.com/ja-jp/news/{article_id}')
                accepted += 1
            print(f'Official discovery: {page}: {len(parser.links)} links, {accepted} article references')
        except Exception as exc:
            print(f'WARNING: Official discovery failed for {page}: {type(exc).__name__}: {exc}')
    print(f'HSR official discovery: {len(found)} unique article URLs found.')
    for url in sorted(found, reverse=True)[:15]:
        print('  ' + url)
    if not found:
        print('NOTE: No article links found. The site may load its news list dynamically; existing importers remain unchanged.')
    else:
        print('NOTE: Discovery only. Article text extraction and safe event reconciliation are NOT implemented yet.')

if __name__ == '__main__':
    main()
