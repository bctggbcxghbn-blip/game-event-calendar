"""Discover official Japanese version-news URLs without changing calendar data."""
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from tools.discover_versions import DOMAIN, discover_html

HREF_RE = re.compile(r'''(?is)<a\b[^>]*?href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>''')
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
