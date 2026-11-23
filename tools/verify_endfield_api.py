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
NAMED_VERSION_RE = re.compile(r'(?:新バージョン|バージョンアップデート[^「]{0,20})[「『]([^」』]{2,40})[」』]|[「『]([^」』]{2,40})[」』]\s*バージョンアップデート')
ASIA_MAINT_RE = re.compile(r'Asiaサーバー\s*[:：]\s*(20\d{2})[/.年](\d{1,2})[/.月](\d{1,2})\s*(\d{1,2}):(\d{2})\s*[～~-]\s*(?:(20\d{2})[/.年](\d{1,2})[/.月](\d{1,2})\s*)?(\d{1,2}):(\d{2})')


def _safe_url(url, host=API_HOST):
    parsed = urlparse(url)
    return parsed.scheme == 'https' and parsed.hostname == host


def _safe_article_url(url):
    return _safe_url(url, ARTICLE_HOST)


def _fetch_article_html(url, timeout=15, opener=urlopen):
    """Fetch an article for read-only identity verification."""
    if not _safe_article_url(url):
        return {'ok': False, 'status': None, 'url': url, 'bytes': 0,
                'reason': 'unsafe_article_url'}
    try:
        req = Request(url, headers={'Accept': 'text/html',
                                    'User-Agent': 'GameEventCalendar-EndfieldAudit/1.0'})
        with opener(req, timeout=timeout) as response:
            raw = response.read(2_000_000)
            final_url = response.geturl()
            if final_url != url or not _safe_article_url(final_url):
                return {'ok': False, 'status': getattr(response, 'status', None),
                        'url': url, 'final_url': final_url, 'bytes': len(raw),
                        'reason': 'unsafe_redirect'}
            return {'ok': True, 'status': getattr(response, 'status', 200),
                    'url': url, 'final_url': final_url, 'bytes': len(raw),
                    'html': raw.decode('utf-8', 'replace')}
    except Exception as exc:
        return {'ok': False, 'status': getattr(exc, 'code', None), 'url': url,
                'bytes': 0, 'reason': type(exc).__name__}


def _normalize_title(value):
    value = re.sub(r'<[^>]*>', ' ', str(value or ''))
    return re.sub(r'\s+', ' ', value).strip().casefold()


def _api_metadata(payload, cid):
    """Read explicit identity fields; never infer absent API fields."""
    obj = payload.get('data') if isinstance(payload, dict) and isinstance(payload.get('data'), dict) else payload
    if not isinstance(obj, dict):
        return {'cid': cid, 'id': None, 'url': None, 'title': None, 'published_at': None}
    def first(keys):
        for key in keys:
            if obj.get(key) not in (None, ''):
                return obj[key]
        return None
    return {'cid': cid, 'id': first(('cid', 'id', 'articleId', 'article_id')),
            'url': first(('url', 'articleUrl', 'article_url', 'link')),
            'title': first(('title', 'name')),
            'published_at': first(('displayTime', 'published_at', 'publishTime', 'createdAt'))}


def _html_metadata(html):
    title = None
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html or '', re.I | re.S)
    if title_match:
        title = title_match.group(1)
    if not title:
        meta = re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:title|title)["\'][^>]+content=["\']([^"\']+)', html or '', re.I)
        title = meta.group(1) if meta else None
    ids = re.findall(r'(?:cid|article(?:Id|_id)|newsId)["\'=:/> ]+(\d+)', html or '', re.I)
    ids.extend(re.findall(r'/ja-jp/news/(\d+)', html or '', re.I))
    dates = re.findall(r'(20\d{2}[/-]\d{1,2}[/-]\d{1,2}(?:[T ]\d{1,2}:\d{2}(?::\d{2})?)?)', html or '')
    return {'title': _normalize_title(title), 'ids': sorted(set(ids)),
            'published_at': dates[0] if dates else None}


def _verify_article_identity(payload, cid, article_result):
    """Return a strict identity decision; HTTP 200 alone is insufficient."""
    meta = _api_metadata(payload, cid)
    html = article_result.get('html', '') if isinstance(article_result, dict) else ''
    hmeta = _html_metadata(html)
    api_ids = {str(meta['cid']), str(meta['id'])} - {'None', ''}
    id_match = bool(api_ids.intersection(hmeta['ids']))
    explicit_url = str(meta.get('url') or '')
    url_match = bool(explicit_url and _safe_article_url(explicit_url)
                     and urlparse(explicit_url).path.rstrip('/') == f'/ja-jp/news/{cid}')
    title_match = bool(meta.get('title') and hmeta['title']
                       and _normalize_title(meta['title']) == hmeta['title'])
    published_match = bool(meta.get('published_at') and hmeta.get('published_at')
                           and str(meta['published_at'])[:10] == str(hmeta['published_at'])[:10])
    verified = id_match or url_match or (title_match and published_match)
    return {'verified': verified, 'method': 'cid' if id_match else ('url' if url_match else ('title_published' if title_match and published_match else None)),
            'api_id': meta.get('id'), 'api_url': meta.get('url'),
            'api_title': meta.get('title'), 'api_published_at': meta.get('published_at'),
            'html_ids': hmeta['ids'], 'html_title': hmeta['title'],
            'html_published_at': hmeta.get('published_at'),
            'reason': None if verified else 'article_identity_mismatch'}


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


def _extract_named_version(payload, cid):
    """Extract a named release only when explicit update wording is present."""
    text = _text(payload)
    match = NAMED_VERSION_RE.search(text)
    name = next((group for group in match.groups() if group), None) if match else None
    maintenance_start = maintenance_end = None
    maintenance = ASIA_MAINT_RE.search(text)
    if maintenance:
        year, month, day, shour, smin, eyear, emonth, eday, ehour, emin = maintenance.groups()
        eyear = eyear or year; emonth = emonth or month; eday = eday or day
        # Asia times are UTC+8; retain the source offset and provide JST too.
        start = dt.datetime(int(year), int(month), int(day), int(shour), int(smin), tzinfo=dt.timezone(dt.timedelta(hours=8)))
        end = dt.datetime(int(eyear), int(emonth), int(eday), int(ehour), int(emin), tzinfo=dt.timezone(dt.timedelta(hours=8)))
        maintenance_start = {'source': start.isoformat(), 'jst': start.astimezone(dt.timezone(dt.timedelta(hours=9))).isoformat()}
        maintenance_end = {'source': end.isoformat(), 'jst': end.astimezone(dt.timezone(dt.timedelta(hours=9))).isoformat()}
    article_url = f'https://{ARTICLE_HOST}/ja-jp/news/{cid}'
    serialized = json.dumps(payload, ensure_ascii=False) if isinstance(payload, (dict, list)) else ''
    mapping_verified = article_url in serialized
    published = None
    if isinstance(payload, dict):
        for key in ('displayTime', 'published_at', 'publishTime', 'createdAt'):
            if isinstance(payload.get(key), (str, int, float)):
                published = payload[key]
                break
        data = payload.get('data')
        if isinstance(data, dict) and published is None:
            for key in ('displayTime', 'published_at', 'publishTime', 'createdAt'):
                if isinstance(data.get(key), (str, int, float)):
                    published = data[key]
                    break
    return {'named_version': name, 'numeric_version': None, 'maintenance_start': maintenance_start,
            'maintenance_end': maintenance_end, 'effective_from': None,
            'article_url': article_url, 'cid_url_mapping_verified': mapping_verified,
            'status': 'official_named' if name and mapping_verified else 'unverified_named',
            'accepted_as_current': False, 'published_at': published}


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


def audit(fetcher=_request, checked_at=None, today=None, article_fetcher=None):
    # Real audits always perform an official HTML GET.  Unit tests may inject
    # an article_fetcher to keep network access deterministic.
    if article_fetcher is None and fetcher is _request:
        article_fetcher = _fetch_article_html
    checked_at = checked_at or dt.datetime.now(dt.timezone.utc).astimezone().isoformat()
    today = today or dt.date.today()
    report = {'status': 'failed', 'listing': {}, 'pages': [], 'article_ids': [],
              'article_inventory': [], 'related_articles': [], 'details': [],
              'candidates': [], 'exclusions': {}, 'priority': [],
              'url_verification': [], 'checked_at': checked_at,
              'read_only': True}
    all_rows, seen_ids, page_signatures = [], set(), set()
    first_page_ok = None
    for page in range(1, MAX_PAGES + 1):
        listing = fetcher(_listing_url(page))
        page_report = {'page': page, 'status': listing.get('status'),
                       'bytes': listing.get('bytes', 0), 'reason': listing.get('reason')}
        report['pages'].append(page_report)
        if page == 1:
            report['listing'] = {k: listing.get(k) for k in ('status', 'bytes', 'reason', 'final_url') if k in listing}
            first_page_ok = bool(listing.get('ok'))
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
                if not cid.isdigit():
                    report['exclusions']['invalid_cid'] = report['exclusions'].get('invalid_cid', 0) + 1
                if cid and cid in seen_ids:
                    report['exclusions']['duplicate_cid'] = report['exclusions'].get('duplicate_cid', 0) + 1
                continue
            seen_ids.add(cid)
            item = {key: row[key] for key in ('cid', 'title', 'brief', 'displayTime', 'tab', 'type') if key in row}
            all_rows.append(item)
        total = (listing.get('payload', {}).get('data', {}).get('total')
                 if isinstance(listing.get('payload'), dict)
                 and isinstance(listing.get('payload', {}).get('data'), dict)
                 else None)
        if total is not None and len(all_rows) >= int(total):
            page_report['termination'] = 'final_page'
            break
    report['article_inventory'] = all_rows
    related = [row for row in all_rows if any(h.lower() in (_text(row.get('title')) + ' ' + _text(row.get('brief'))).lower() for h in RELATED_HINTS)]
    report['related_articles'] = related
    def priority_rank(row):
        title = _text(row.get('title'))
        brief = _text(row.get('brief'))
        if 'バージョンアップデート' in title:
            return 0
        if '新バージョン' in brief:
            return 1
        if 'メンテナンス' in title + brief:
            return 2
        return 3
    rows = sorted(all_rows, key=priority_rank)
    report['priority'] = [{'cid': row.get('cid'), 'priority': 'title_update' if 'バージョンアップデート' in _text(row.get('title')) else ('brief_new_version' if '新バージョン' in _text(row.get('brief')) else ('maintenance' if 'メンテナンス' in (_text(row.get('title')) + _text(row.get('brief'))) else 'normal'))} for row in rows]
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
    body_verified_count = 0
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
        diagnostics['named_version'] = _extract_named_version(detail.get('payload'), cid)
        article_result = article_fetcher(article_url) if article_fetcher else {'ok': False, 'reason': 'article_fetch_disabled'}
        identity = _verify_article_identity(detail.get('payload'), cid, article_result) if article_result.get('ok') else {'verified': False, 'method': None, 'reason': article_result.get('reason', 'article_fetch_failed')}
        item['article_fetch'] = {k: article_result.get(k) for k in ('status', 'bytes', 'final_url', 'reason') if k in article_result}
        item['url_verification'] = identity
        report['url_verification'].append({'cid': cid, **identity})
        if not identity['verified']:
            diagnostics['exclusion_reasons'].append('article_url_unverified')
            report['exclusions']['article_url_unverified'] = report['exclusions'].get('article_url_unverified', 0) + 1
        item['diagnostics'] = diagnostics
        for reason in diagnostics['exclusion_reasons']:
            report['exclusions'][reason] = report['exclusions'].get(reason, 0) + 1
        # The reconstructed URL contains ``ja-jp`` by definition; require
        # Japanese/JP evidence in the API body itself as well.
        if not re.search(r'日本|日本語|Asia|アジア|JP', body, re.I):
            body_candidate = None
        else:
            body_candidate = discover_html('endfield', body, article_url, checked_at, today=today)
        if body_candidate:
            body_verified_count += 1
        candidate = body_candidate if identity['verified'] else None
        if candidate:
            report['candidates'].append(candidate)
        else:
            report['exclusions']['body_not_verified'] = report['exclusions'].get('body_not_verified', 0) + 1
    if first_page_ok is False:
        report['status'] = 'failed'
    else:
        report['status'] = 'success' if report['candidates'] else 'unverified'
    report['article_detail_successes'] = sum(1 for x in report['details'] if x.get('reason') is None and x.get('status') is not None)
    report['body_verification_successes'] = body_verified_count
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
