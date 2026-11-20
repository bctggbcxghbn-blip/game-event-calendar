"""Discover official Japanese version-news URLs without changing calendar data."""
import re
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from tools.discover_versions import DOMAIN, discover_html

HREF_RE = re.compile(r'''(?is)<a\b[^>]*?href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>''')
SCRIPT_URL_RE = re.compile(r'''https://endfield\.gryphline\.com/[^"'\\s<>]+''', re.I)
VERSION_HINT = re.compile(r'(?i)(?:ver(?:sion)?\.?\s*\d+(?:\.\d+)+|バージョン\s*\d+(?:\.\d+)+|アップデート|update)')

# These are conservative landing pages only; article URLs are accepted after
# redirect and host validation. They are not used by Actions in this PR.
NEWS_INDEX = {
    'genshin': 'https://www.hoyolab.com/genshin-impact',
    'wuwa': 'https://wutheringwaves.kurogames.com/jp/main/news',
    'hsr': 'https://www.hoyolab.com/honkai-star-rail',
    'zzz': 'https://www.hoyolab.com/zenless-zone-zero',
    'nte': 'https://nte.perfectworld.com/jp/article/news/gamenews',
    'endfield': 'https://endfield.gryphline.com/ja-jp/news',
}


def _allowed(game, url):
    return urlparse(url).scheme == 'https' and urlparse(url).hostname in DOMAIN.get(game, set())


def discover_links(game, listing_html, listing_url):
    """Find unique, same-provider version-news links from a listing snapshot."""
    return discover_links_diagnostic(game, listing_html, listing_url)[0]


def discover_links_diagnostic(game, listing_html, listing_url):
    """Return links plus counts/reasons without relaxing official checks."""
    stats = {'html_links': 0, 'official_links': 0, 'version_candidates': 0,
             'rejected_external': 0, 'rejected_no_version_hint': 0, 'article_urls': 0}
    if game not in NEWS_INDEX or not _allowed(game, listing_url):
        return [], stats
    found = []
    for href, title in HREF_RE.findall(listing_html or ''):
        stats['html_links'] += 1
        url = urljoin(listing_url, href)
        text = re.sub(r'<[^>]+>', ' ', title)
        if not _allowed(game, url):
            stats['rejected_external'] += 1
            continue
        stats['official_links'] += 1
        if VERSION_HINT.search(text + ' ' + href):
            stats['version_candidates'] += 1
            if url not in found:
                found.append(url)
        else:
            stats['rejected_no_version_hint'] += 1
    stats['article_urls'] = len(found)
    return found, stats


def diagnose_endfield_links(listing_html, listing_url, sample_limit=30):
    """Classify Endfield links without expanding the automatic fetch set."""
    result = {
        'official_link_samples': [], 'article_path_links': 0,
        'rejected_wrong_path': 0, 'rejected_invalid_article_id': 0,
        'script_json_article_urls': 0, 'article_urls_considered': 0,
    }
    if not _allowed('endfield', listing_url):
        return result
    seen = set()
    for href, _title in HREF_RE.findall(listing_html or ''):
        url = urljoin(listing_url, href)
        parsed = urlparse(url)
        if parsed.hostname not in DOMAIN['endfield'] or parsed.scheme != 'https':
            continue
        # Do not expose tokens or arbitrary query values in diagnostics.
        safe_query = ''
        query = parse_qs(parsed.query)
        if 'id' in query and query['id'] and query['id'][0].isdigit():
            safe_query = 'id=' + query['id'][0]
        safe_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', safe_query, ''))
        if safe_url in seen:
            continue
        seen.add(safe_url)
        path = parsed.path.rstrip('/')
        classification = 'other'
        if path == '/ja-jp/news':
            classification = 'news_index'
        elif path.startswith('/ja-jp/news/'):
            article_id = path.rsplit('/', 1)[-1]
            if article_id.isdigit():
                classification = 'valid_article_path'
                result['article_path_links'] += 1
            else:
                classification = 'invalid_article_id'
                result['rejected_invalid_article_id'] += 1
        else:
            classification = 'wrong_path'
            result['rejected_wrong_path'] += 1
        if len(result['official_link_samples']) < sample_limit:
            result['official_link_samples'].append({'url': safe_url, 'path': parsed.path,
                                                    'classification': classification})
    urls = set(SCRIPT_URL_RE.findall(listing_html or ''))
    result['script_json_article_urls'] = sum(1 for url in urls if '/ja-jp/news/' in url)
    return result


def discover_endfield_body_candidates(listing_html, listing_url, article_pages,
                                      checked_at, today=None, max_articles=20):
    """Inspect Endfield article bodies when listing titles lack version hints.

    This fallback is deliberately Endfield-only.  It never accepts a title or
    a proper-name version by itself; ``discover_html`` still requires an
    explicit numeric version, Japanese/JP context, and an effective date.
    """
    stats = {'article_urls_considered': 0, 'article_fetch_failures': 0,
             'body_candidates': 0, 'rejected_no_version': 0,
             'rejected_no_effective_date_or_region': 0, 'rejected_future': 0,
             'rejected_proper_name_only': 0}
    if not _allowed('endfield', listing_url):
        return [], stats
    links = []
    for href, _title in HREF_RE.findall(listing_html or ''):
        url = urljoin(listing_url, href)
        if _allowed('endfield', url) and '/ja-jp/news/' in url and url not in links:
            links.append(url)
    rows = []
    for url in links[:max_articles]:
        stats['article_urls_considered'] += 1
        html = article_pages.get(url)
        if html is None:
            stats['article_fetch_failures'] += 1
            continue
        text = re.sub(r'<[^>]+>', ' ', html or '')
        # A named update such as 丹青渡 is useful for diagnostics, but is not
        # a numeric version candidate and therefore cannot update JSON.
        if '丹青渡' in text and not re.search(r'(?i)\b(?:ver(?:sion)?\.?|バージョン)\s*\d+(?:\.\d+)+', text):
            stats['rejected_proper_name_only'] += 1
        row = discover_html('endfield', html, url, checked_at, today=today)
        if row:
            rows.append(row)
            stats['body_candidates'] += 1
            continue
        if not re.search(r'(?i)\b(?:ver(?:sion)?\.?|バージョン)\s*\d+(?:\.\d+)+', text):
            stats['rejected_no_version'] += 1
        else:
            stats['rejected_no_effective_date_or_region'] += 1
    return rows, stats


def fetch_listing(game, url=None, timeout=15):
    """Fetch a listing and reject redirects outside the official allow-list."""
    url = url or NEWS_INDEX.get(game)
    if game not in NEWS_INDEX or not _allowed(game, url):
        return None
    try:
        response = urlopen(Request(url, headers={'User-Agent': 'GameEventCalendar/1.0'}), timeout=timeout)
        final_url = response.geturl()
        if not _allowed(game, final_url):
            return None
        return final_url, response.read().decode('utf-8', 'replace')
    except OSError:
        return None


def discover_candidates(game, listing_html, listing_url, article_pages, checked_at, today=None):
    """Convert discovered article snapshots to PR2 candidate rows."""
    rows = []
    for url in discover_links(game, listing_html, listing_url):
        html = article_pages.get(url)
        if html is None:
            continue
        row = discover_html(game, html, url, checked_at, today=today)
        if row and row not in rows:
            rows.append(row)
    return rows
