"""V80 read-only: inspect allowlisted Endfield JS assets for news API clues."""
import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import Request, urlopen

NEWS = 'https://endfield.gryphline.com/ja-jp/news'
ALLOWED_HOSTS = {'endfield.gryphline.com', 'web-static.hg-cdn.com'}
MAX_BYTES = 3_000_000
MAX_ASSETS = 8
URL_PATTERN = re.compile(r'https?://[^\s"\'`<>\\]{5,250}|/[\w./?=&%+\-]{6,200}', re.I)
KEYWORD = re.compile(r'news|article|notice|api|graphql|information|list|content|cms', re.I)
CDN_JS = re.compile(r'https?://web-static\.hg-cdn\.com/[^\s"\'`<>]+?\.js', re.I)

class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            src = dict(attrs).get('src')
            if src:
                self.scripts.append(src)

def allowed(url):
    p = urlparse(url)
    return p.scheme == 'https' and p.hostname in ALLOWED_HOSTS and not p.username and not p.password

def assets_from_html(html, base=NEWS):
    parser = ScriptParser()
    parser.feed(html)
    raw = [urljoin(base, src) for src in parser.scripts]
    raw.extend(m.group(0) for m in CDN_JS.finditer(html.replace('\\/', '/')))
    # Next.js page JS is often referenced in RSC data rather than script tags.
    raw.extend(m.group(0) for m in CDN_JS.finditer(html))
    return list(dict.fromkeys(url for url in raw if allowed(url) and urlparse(url).path.endswith('.js')))

def clues(body, limit=40):
    found = []
    for match in URL_PATTERN.finditer(body.replace('\\/', '/')):
        item = match.group(0).rstrip('.,;:')[:220]
        if KEYWORD.search(item) and item not in found:
            found.append(item)
        if len(found) >= limit:
            break
    return found

def fetch(url):
    if not allowed(url):
        raise ValueError('Host not on official-site/CDN allowlist')
    req = Request(url, headers={'User-Agent': 'GameEventCalendar-EndfieldDiagnostics/80', 'Accept': 'text/html,application/javascript,*/*'})
    with urlopen(req, timeout=20) as response:
        if not allowed(response.geturl()):
            raise ValueError('Redirected outside allowlist')
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Response too large')
        return raw.decode('utf-8', 'replace'), response.status, response.geturl()

def run(fetcher=fetch, max_assets=MAX_ASSETS):
    report = {'version': 80, 'mode': 'read_only_cdn_js_diagnostics', 'page': NEWS,
              'assets': [], 'endpoint_candidates': [], 'events_added': 0,
              'automatically_approved': 0}
    try:
        html, status, final = fetcher(NEWS)
        report['page_status'] = status
        report['page_final_url'] = final
    except Exception as exc:
        report['page_error'] = str(exc)[:200]
        return report
    candidates = assets_from_html(html, final)
    # Prior V79 identified this exact official CDN bundle; use it if page parsing changes.
    fallback = 'https://web-static.hg-cdn.com/endfield/official-v4/_next/static/chunks/app/%5Blang%5D/(main)/(subpage)/news/page-845bebead983deba.js'
    if fallback not in candidates:
        candidates.insert(0, fallback)
    candidates.sort(key=lambda url: ('/news/page-' not in unquote(url), url))
    report['script_assets_found'] = len(candidates)
    hints = []
    for url in candidates[:max_assets]:
        item = {'url': url}
        try:
            body, status, final_url = fetcher(url)
            item.update({'status': status, 'final_url': final_url, 'characters': len(body)})
            item['hints'] = clues(body)
            hints.extend(item['hints'])
            item['keyword_counts'] = {k: len(re.findall(k, body, re.I)) for k in ('news', 'article', 'api', 'graphql', 'cms')}
        except Exception as exc:
            item['error'] = str(exc)[:200]
        report['assets'].append(item)
    report['endpoint_candidates'] = list(dict.fromkeys(hints))[:100]
    report['warning'] = 'Candidate strings are not verified endpoints. No API calls, approvals, or event modifications.'
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='.reports/endfield-v80/report.json')
    parser.add_argument('--max-assets', type=int, default=MAX_ASSETS)
    args = parser.parse_args()
    report = run(max_assets=max(1, min(args.max_assets, 15)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('V80 assets:', len(report['assets']), 'endpoint hints:', len(report['endpoint_candidates']))
