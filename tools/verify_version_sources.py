"""Read-only live audit of official version-news sources."""
import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from tools.discover_version_news import NEWS_INDEX, discover_links
from tools.discover_versions import discover_html


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirect())


def fetch(url, timeout):
    try:
        response = OPENER.open(Request(url, headers={'User-Agent': 'GameEventCalendar-VersionAudit/1.0'}), timeout=timeout)
        return {'ok': True, 'status': getattr(response, 'status', 200), 'final_url': response.geturl(),
                'html': response.read().decode('utf-8', 'replace')}
    except HTTPError as exc:
        return {'ok': False, 'status': exc.code, 'reason': 'http_error', 'final_url': exc.geturl()}
    except URLError as exc:
        return {'ok': False, 'status': None, 'reason': 'network_error', 'detail': str(exc.reason)}
    except TimeoutError:
        return {'ok': False, 'status': None, 'reason': 'timeout'}
    except OSError as exc:
        return {'ok': False, 'status': None, 'reason': 'read_error', 'detail': str(exc)}


def audit(timeout=15, max_articles=5):
    checked_at = dt.datetime.now(dt.timezone.utc).astimezone().isoformat()
    report = {'checked_at': checked_at, 'read_only': True, 'games': {}}
    today = dt.date.today()
    for game, listing_url in NEWS_INDEX.items():
        row = {'listing_url': listing_url, 'status': 'failed', 'article_urls': [], 'candidates': [], 'errors': []}
        listing = fetch(listing_url, timeout)
        if not listing.get('ok'):
            row['errors'].append({k: listing[k] for k in ('reason', 'status', 'detail') if k in listing})
            report['games'][game] = row
            continue
        if listing.get('final_url') != listing_url:
            row['errors'].append({'reason': 'redirect_rejected', 'final_url': listing.get('final_url')})
            report['games'][game] = row
            continue
        links = discover_links(game, listing.get('html', ''), listing_url)
        row['article_urls'] = links[:max_articles]
        for url in row['article_urls']:
            article = fetch(url, timeout)
            if not article.get('ok'):
                row['errors'].append({'url': url, 'reason': article.get('reason'), 'status': article.get('status')})
                continue
            if article.get('final_url') != url:
                row['errors'].append({'url': url, 'reason': 'redirect_rejected', 'final_url': article.get('final_url')})
                continue
            candidate = discover_html(game, article.get('html', ''), url, checked_at, today=today)
            if candidate:
                row['candidates'].append(candidate)
        row['status'] = 'success' if row['candidates'] else ('unverified' if row['article_urls'] else 'failed')
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
