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
from tools.discover_versions import DATE_RE, VERSION_RE

API_HOST = 'web-news.gryphline.com'
API_BASE = 'https://' + API_HOST + '/api/bulletin'
APP_CODE = 'arknights_endfield_official'
LANG = 'ja-jp'
ARTICLE_HOST = 'endfield.gryphline.com'
MAX_DETAILS = 20
MAX_PAGES = 20
RELATED_HINTS = ('バージョン', 'アップデート', 'メンテナンス', '丹青渡', 'version', 'update')


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


def _diagnose_article(payload, cid, today):
    """Return metadata and reasons without retaining article text."""
    body = _text(payload)
    japanese = bool(re.search(r'[ぁ-んァ-ヶ一-龯]', body))
    region = bool(re.search(r'日本向け|日本版|Asia|アジア|\bJP\b', body, re.I))
    version = VERSION_RE.search(body)
    date = DATE_RE.search(body)
    effective = None
    future = False
    if date:
        effective = f'{date.group(1)}-{int(date.group(2)):02d}-{int(date.group(3)):02d}'
        try:
            future = dt.date.fromisoformat(effective) > today
        except ValueError:
            effective = None
    reasons = []
    if not japanese:
        reasons.append('missing_japanese_context')
    if not region:
        reasons.append('missing_region_context')
    if not version:
        reasons.append('missing_numeric_version')
    if not date or not effective:
        reasons.append('missing_effective_date')
    elif future:
        reasons.append('future_effective_date')
    if not isinstance(payload, (dict, list)) or not body.strip():
        reasons.append('invalid_detail_schema')
    return {
        'field_type': type(payload).__name__,
        'text_length': len(body),
        'has_japanese': japanese,
        'has_region_context': region,
        'has_numeric_version': bool(version),
        'has_date': bool(date),
        'effective_date': effective,
        'future_effective_date': future,
        'article_url': f'https://{ARTICLE_HOST}/ja-jp/news/{cid}',
        'cid_url_mapping': 'constructed_from_numeric_cid',
        'exclusion_reasons': reasons,
    }


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


def _listing_url(page):
    return API_BASE + '?' + urlencode({'lang': LANG, 'code': APP_CODE,
                                       'page': str(page), 'pageSize': '20'})


def _listing_items(payload):
    data = payload.get('data') if isinstance(payload, dict) else None
    rows = data.get('list') if isinstance(data, dict) else None
    return rows if isinstance(rows, list) else None


def audit(fetcher=_request, checked_at=None, today=None):
    checked_at = checked_at or dt.datetime.now(dt.timezone.utc).astimezone().isoformat()
    today = today or dt.date.today()
    report = {'status': 'failed', 'listing': {}, 'pages': [], 'article_ids': [],
              'article_inventory': [], 'related_articles': [], 'details': [],
              'candidates': [], 'exclusions': {}, 'checked_at': checked_at,
              'read_only': True}
    all_rows, seen_ids, page_signatures = [], set(), set()
    for page in range(1, MAX_PAGES + 1):
        listing = fetcher(_listing_url(page))
        page_report = {'page': page, 'status': listing.get('status'),
                       'bytes': listing.get('bytes', 0), 'reason': listing.get('reason')}
        report['pages'].append(page_report)
        if page == 1:
            report['listing'] = {k: listing.get(k) for k in ('status', 'bytes', 'reason', 'final_url') if k in listing}
        if not listing.get('ok'):
            report['exclusions']['listing_failed'] = report['exclusions'].get('listing_failed', 0) + 1
            break
        rows = _listing_items(listing.get('payload'))
        if rows is None:
            report['exclusions']['invalid_list_schema'] = report['exclusions'].get('invalid_list_schema', 0) + 1
            break
        page_ids = tuple(str(row.get('cid')) for row in rows if isinstance(row, dict) and str(row.get('cid') or '').isdigit())
        page_report['item_count'] = len(rows)
        page_report['valid_cid_count'] = len(page_ids)
        if not rows or page_ids in page_signatures:
            page_report['termination'] = 'empty_page' if not rows else 'duplicate_page'
            break
        page_signatures.add(page_ids)
        for row in rows:
            if not isinstance(row, dict):
                continue
            cid = str(row.get('cid') or '')
            if not cid.isdigit() or cid in seen_ids:
                if cid and cid in seen_ids:
                    report['exclusions']['duplicate_cid'] = report['exclusions'].get('duplicate_cid', 0) + 1
                continue
            seen_ids.add(cid)
            item = {key: row[key] for key in ('cid', 'title', 'brief', 'displayTime', 'tab', 'type') if key in row}
            all_rows.append(item)
        if len(rows) < 20:
            page_report['termination'] = 'final_page'
            break
    report['article_inventory'] = all_rows
    related = [row for row in all_rows if any(h.lower() in (_text(row.get('title')) + ' ' + _text(row.get('brief'))).lower() for h in RELATED_HINTS)]
    report['related_articles'] = related
    rows = related + [row for row in all_rows if row not in related]
    report['listing']['pages_fetched'] = len(report['pages'])
    report['listing']['articles_fetched'] = len(all_rows)
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
            item['diagnostics'] = {'field_type': None, 'text_length': 0,
                                   'has_japanese': False, 'has_region_context': False,
                                   'has_numeric_version': False, 'has_date': False,
                                   'effective_date': None, 'future_effective_date': False,
                                   'article_url': f'https://{ARTICLE_HOST}/ja-jp/news/{cid}',
                                   'cid_url_mapping': 'constructed_from_numeric_cid',
                                   'exclusion_reasons': ['detail_fetch_failed']}
            report['exclusions']['detail_failed'] = report['exclusions'].get('detail_failed', 0) + 1
            report['exclusions']['detail_fetch_failed'] = report['exclusions'].get('detail_fetch_failed', 0) + 1
            continue
        body = _text(detail.get('payload'))
        article_url = f'https://{ARTICLE_HOST}/ja-jp/news/{cid}'
        diagnostics = _diagnose_article(detail.get('payload'), cid, today)
        item['diagnostics'] = diagnostics
        for reason in diagnostics['exclusion_reasons']:
            report['exclusions'][reason] = report['exclusions'].get(reason, 0) + 1
        # The reconstructed URL contains ``ja-jp`` by definition; require
        # Japanese/JP evidence in the API body itself as well.
        if not re.search(r'日本|日本語|Asia|アジア|JP', body, re.I):
            candidate = None
        else:
            candidate = discover_html('endfield', body, article_url, checked_at, today=today)
        if candidate:
            report['candidates'].append(candidate)
        else:
            report['exclusions']['body_not_verified'] = report['exclusions'].get('body_not_verified', 0) + 1
    report['status'] = 'success' if report['candidates'] else 'unverified'
    report['article_detail_successes'] = sum(1 for x in report['details'] if x.get('reason') is None and x.get('status') is not None)
    report['body_verification_successes'] = len(report['candidates'])
    report['exclusion_counts'] = dict(report['exclusions'])
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
