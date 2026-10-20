#!/usr/bin/env python3
"""Read-only Endfield official news monitor; never writes events.json."""
import argparse
import datetime as dt
import html
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = 'https://endfield.gryphline.com'
LIST = BASE + '/ja-jp/news'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; calendar-event-monitor/1.0)'}
KEYWORDS = ('開催期間', 'イベント', 'スカウト', '申請', 'スタンプラリー', '復刻', 'ピックアップ', 'メンテナンス')
DATE = re.compile(r'20\d{2}\s*[/年.-]\s*\d{1,2}\s*[/月.-]\s*\d{1,2}')
ARTICLE = re.compile(r'(?:https?://endfield\.gryphline\.com)?/ja-jp/news/(\d{3,8})')

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = set()
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.text.append(' ')
        if tag == 'a':
            href = dict(attrs).get('href', '')
            match = ARTICLE.search(href)
            if match:
                self.links.add(BASE + '/ja-jp/news/' + match.group(1))
        if tag in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'br'):
            self.text.append('\n')
    def handle_data(self, data):
        self.text.append(data)

def parse_page(source):
    p = Page()
    p.feed(source)
    # Also inspect JSON-embedded links, common on JS-driven news listings.
    for match in ARTICLE.finditer(html.unescape(source).replace('\\/', '/')):
        p.links.add(BASE + '/ja-jp/news/' + match.group(1))
    return p

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read().decode('utf-8', 'replace')

def extract_candidates(source):
    p = parse_page(source)
    raw = html.unescape(''.join(p.text))
    lines = [re.sub(r'\s+', ' ', x).strip() for x in raw.splitlines()]
    lines = [x for x in lines if x]
    candidates = []
    for i, line in enumerate(lines):
        if any(k in line for k in KEYWORDS) or DATE.search(line):
            context = ' '.join(lines[max(0, i-1):min(len(lines), i+2)])[:600]
            if context not in candidates:
                candidates.append(context)
    return candidates[:250]

def discover(fetcher=fetch, limit=20):
    listing = fetcher(LIST)
    urls = sorted(parse_page(listing).links)[:limit]
    # Always include the known version notice, even if pagination hides it.
    known = BASE + '/ja-jp/news/9560'
    if known not in urls:
        urls.append(known)
    articles = []
    errors = []
    for url in urls:
        try:
            src = fetcher(url)
            lines = extract_candidates(src)
            articles.append({'url': url, 'candidate_count': len(lines), 'candidate_text': lines})
        except Exception as e:
            errors.append({'url': url, 'error': str(e)[:200]})
    return {'version': 73, 'checked_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'listing_url': LIST, 'article_count': len(articles), 'articles': articles,
            'fetch_errors': errors, 'auto_imported': 0, 'mode': 'read-only'}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='reports/endfield-v73-candidates.json')
    ap.add_argument('--limit', type=int, default=20)
    args = ap.parse_args()
    report = discover(limit=max(1, min(args.limit, 50)))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Endfield V73 articles={report['article_count']} errors={len(report['fetch_errors'])} auto_imported=0")
    if not report['articles']:
        raise SystemExit('No articles retrieved; check source site/network')

if __name__ == '__main__':
    main()
