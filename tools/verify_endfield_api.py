"""Read-only audit of Endfield's first-party bulletin API.

This module never writes calendar/version data.  It returns diagnostics and
only treats an API item as a candidate after the existing strict article-body
validator accepts the reconstructed official Japanese article URL.
"""
import datetime as dt
import json
import re
from pathlib import Path
import argparse
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from tools.discover_versions import discover_html

API_HOST = 'web-news.gryphline.com'
API_BASE = 'https://' + API_HOST + '/api/bulletin'
APP_CODE = 'arknights_endfield_official'
LANG = 'ja-jp'
ARTICLE_HOST = 'endfield.gryphline.com'
MAX_DETAILS = 20


def _safe_url(url, host=API_HOST):
    parsed = urlparse(url)
    return parsed.scheme == 'https' and parsed.hostname == host


def _text(value):
    if isinstance(value, str):
        return re.sub(r'<[^>]*>', ' ', value)
    if isinstance(value, dict):
        return ' '.join(_text(v) for v in value.values())
    if isinstance(value, list):
        return ' '.join(_text(v) for v in value)
    return ''


def _request(url, timeout=15, opener=urlopen):
    if not _safe_url(url):
        return {'ok': False, 'status': None, 'url': url, 'bytes': 0, 'reason': 'unsafe_url'}
    try:
        req = Request(url, headers={'Accept': 'application/json',
                                    'User-Agent': 'GameEventCalendar-EndfieldAudit/1.0'})
        with opener(req, timeout=timeout) as response:
            raw = response.read(2_000_000)
            if response.geturl() != url or not _safe_url(response.geturl()):
                return {'ok': False, 'status': getattr(response, 'status', None), 'url': url,
                        'final_url': response.geturl(), 'bytes': len(raw), 'reason': 'unsafe_redirect'}
            try:
                payload = json.loads(raw.decode('utf-8', 'replace'))
            except (ValueError, TypeError):
                return {'ok': False, 'status': getattr(response, 'status', None), 'url': url,
                        'bytes': len(raw), 'reason': 'invalid_json'}
            return {'ok': True, 'status': getattr(response, 'status', 200), 'url': url,
                    'final_url': response.geturl(), 'bytes': len(raw), 'payload': payload}
    except Exception as exc:
        return {'ok': False, 'status': getattr(exc, 'code', None), 'url': url,
                'bytes': 0, 'reason': type(exc).__name__}


def audit(fetcher=_request, checked_at=None, today=None):
    checked_at = checked_at or dt.datetime.now(dt.timezone.utc).astimezone().isoformat()
    today = today or dt.date.today()
    query = urlencode({'lang': LANG, 'code': APP_CODE, 'page': '1', 'pageSize': '20'})
    listing_url = API_BASE + '?' + query
    report = {'status': 'failed', 'listing': {}, 'article_ids': [], 'details': [],
              'candidates': [], 'exclusions': {}, 'checked_at': checked_at,
              'read_only': True}
    listing = fetcher(listing_url)
    report['listing'] = {k: listing.get(k) for k in ('status', 'bytes', 'reason', 'final_url') if k in listing}
    if not listing.get('ok'):
        report['exclusions']['listing_failed'] = 1
        return report
    payload = listing.get('payload')
    data = payload.get('data') if isinstance(payload, dict) else None
    rows = data.get('list') if isinstance(data, dict) else None
    if not isinstance(rows, list):
        report['exclusions']['invalid_list_schema'] = 1
        return report
    ids = []
    for row in rows:
        cid = row.get('cid') if isinstance(row, dict) else None
        if not str(cid or '').isdigit():
            report['exclusions']['invalid_cid'] = report['exclusions'].get('invalid_cid', 0) + 1
            continue
        cid = str(cid)
        if cid not in ids:
            ids.append(cid)
    report['article_ids'] = ids[:MAX_DETAILS]
    report['article_id_sample'] = report['article_ids'][:10]
    for cid in report['article_ids']:
        detail_url = API_BASE + '/' + cid + '?' + urlencode({'lang': LANG, 'code': APP_CODE})
        detail = fetcher(detail_url)
        item = {'cid': cid, 'status': detail.get('status'), 'bytes': detail.get('bytes', 0),
                'reason': detail.get('reason')}
        report['details'].append(item)
        if not detail.get('ok'):
            report['exclusions']['detail_failed'] = report['exclusions'].get('detail_failed', 0) + 1
            continue
        body = _text(detail.get('payload'))
        article_url = f'https://{ARTICLE_HOST}/ja-jp/news/{cid}'
        candidate = discover_html('endfield', body, article_url, checked_at, today=today)
        if candidate:
            report['candidates'].append(candidate)
        else:
            report['exclusions']['body_not_verified'] = report['exclusions'].get('body_not_verified', 0) + 1
    report['status'] = 'success' if report['candidates'] else 'unverified'
    report['article_detail_successes'] = sum(1 for x in report['details'] if x.get('reason') is None and x.get('status') is not None)
    report['body_verification_successes'] = len(report['candidates'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=Path('artifacts/endfield-api-audit/report.json'))
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'article_ids': len(report['article_ids']),
                      'details': len(report['details']),
                      'candidates': len(report['candidates']),
                      'output': str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
