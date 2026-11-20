"""Read-only live audit of official version-news sources."""
import argparse
import datetime as dt
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from tools.discover_version_news import NEWS_INDEX, diagnose_endfield_links, discover_links_diagnostic
from tools.discover_versions import DOMAIN
from tools.discover_versions import discover_html


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirect())


def fetch(url, timeout, game=None, max_redirects=2):
    requested = url
    redirects = []
    started = time.monotonic()
    for _ in range(max_redirects + 1):
      try:
        response = OPENER.open(Request(url, headers={'User-Agent': 'GameEventCalendar-VersionAudit/1.0'}), timeout=timeout)
        html = response.read().decode('utf-8', 'replace')
        return {'ok': True, 'status': getattr(response, 'status', 200), 'requested_url': requested,
                'final_url': response.geturl(), 'redirects': redirects, 'html': html,
                'html_bytes': len(html.encode('utf-8')), 'elapsed_ms': round((time.monotonic()-started)*1000)}
      except HTTPError as exc:
        location = exc.headers.get('Location')
        if exc.code in (301,302,303,307,308) and location:
            from urllib.parse import urljoin, urlparse
            target = urljoin(url, location)
            redirects.append({'from': url, 'to': target, 'status': exc.code})
            parsed = urlparse(target)
            if len(redirects)>max_redirects or parsed.scheme != 'https' or parsed.hostname not in DOMAIN.get(game, set()):
                return {'ok': False, 'status': exc.code, 'requested_url': requested, 'final_url': target,
                        'redirects': redirects, 'reason': 'redirect_rejected', 'elapsed_ms': round((time.monotonic()-started)*1000)}
            url = target
            continue
        return {'ok': False, 'status': exc.code, 'requested_url': requested, 'final_url': exc.geturl(),
                'redirects': redirects, 'reason': 'http_error', 'elapsed_ms': round((time.monotonic()-started)*1000)}
      except URLError as exc:
        return {'ok': False, 'status': None, 'requested_url': requested, 'final_url': url, 'redirects': redirects, 'reason': 'network_error', 'detail': str(exc.reason), 'elapsed_ms': round((time.monotonic()-started)*1000)}
      except TimeoutError:
        return {'ok': False, 'status': None, 'requested_url': requested, 'final_url': url, 'redirects': redirects, 'reason': 'timeout', 'elapsed_ms': round((time.monotonic()-started)*1000)}
      except OSError as exc:
        return {'ok': False, 'status': None, 'requested_url': requested, 'final_url': url, 'redirects': redirects, 'reason': 'read_error', 'detail': str(exc), 'elapsed_ms': round((time.monotonic()-started)*1000)}


def audit(timeout=15, max_articles=5):
    checked_at = dt.datetime.now(dt.timezone.utc).astimezone().isoformat()
    report = {'checked_at': checked_at, 'read_only': True, 'games': {}}
    today = dt.date.today()
    for game, listing_url in NEWS_INDEX.items():
        row = {'listing_url': listing_url, 'status': 'failed', 'article_urls': [], 'candidates': [], 'errors': [], 'diagnostics': {}}
        listing = fetch(listing_url, timeout, game=game)
        row['diagnostics']['listing'] = {k: listing.get(k) for k in ('status','requested_url','final_url','html_bytes','elapsed_ms','redirects')}
        if not listing.get('ok'):
            row['errors'].append({k: listing[k] for k in ('reason', 'status', 'detail','final_url') if k in listing})
            report['games'][game] = row
            continue
        links, link_stats = discover_links_diagnostic(game, listing.get('html', ''), listing_url)
        if game == 'endfield':
            link_stats['endfield_url_diagnostics'] = diagnose_endfield_links(
                listing.get('html', ''), listing_url)
        row['diagnostics']['discovery'] = link_stats
        row['article_urls'] = links[:max_articles]
        if not row['article_urls']:
            row['errors'].append({'reason': 'no_article_links_found'})
        for url in row['article_urls']:
            article = fetch(url, timeout, game=game)
            row['diagnostics'].setdefault('articles', []).append({k: article.get(k) for k in ('status','requested_url','final_url','html_bytes','elapsed_ms','redirects')})
            if not article.get('ok'):
                row['errors'].append({'url': url, 'reason': article.get('reason'), 'status': article.get('status')})
                continue
            if article.get('final_url') != url:
                row['errors'].append({'url': url, 'reason': 'redirect_rejected', 'final_url': article.get('final_url')})
                continue
            candidate = discover_html(game, article.get('html', ''), url, checked_at, today=today)
            if candidate:
                row['candidates'].append(candidate)
            else:
                row['errors'].append({'url': url, 'reason': 'version_candidate_not_verified'})
        row['status'] = 'success' if row['candidates'] else ('unverified' if row['article_urls'] else 'failed')
        if row['status'] == 'failed' and not row['errors']:
            row['errors'].append({'reason': 'verification_failed_unknown'})
        report['games'][game] = row
    return report


def write_report(report, json_path, markdown_path):
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# Version source live audit', '', f"確認日時: {report['checked_at']}", '', '| ゲーム | 状態 | 記事URL数 | 候補数 |', '|---|---|---:|---:|']
    for game, row in report['games'].items():
        lines.append(f"| {game} | {row['status']} | {len(row['article_urls'])} | {len(row['candidates'])} |")
    markdown_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', type=Path, default=Path('artifacts/version-sources/report.json'))
    parser.add_argument('--markdown', type=Path, default=Path('artifacts/version-sources/report.md'))
    args = parser.parse_args()
    report = audit()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    write_report(report, args.json, args.markdown)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
