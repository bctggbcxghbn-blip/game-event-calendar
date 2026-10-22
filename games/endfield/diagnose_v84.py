#!/usr/bin/env python3
"""Read-only, bounded probes of the Endfield official bulletin API."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOST = 'https://web-news.gryphline.com'
APP_CODE = 'arknights_endfield_official'
OUT = Path('.reports/endfield-v84/report.json')
MAX_BYTES = 1_500_000
TIMEOUT = 12
USER_AGENT = 'GameEventCalendar-Diagnostics/1.0'


def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://endfield.gryphline.com/ja-jp/news',
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                return {'status': response.status, 'content_type': response.headers.get('Content-Type', ''), 'error': 'response_size_limit'}
            text = raw.decode('utf-8', 'replace')
            result = {'status': response.status, 'content_type': response.headers.get('Content-Type', ''), 'body': text}
            try:
                result['json'] = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                pass
            return result
    except urllib.error.HTTPError as exc:
        try:
            snippet = exc.read(800).decode('utf-8', 'replace')
        except Exception:
            snippet = ''
        return {'status': exc.code, 'error': 'http_error', 'body_preview': snippet[:300]}
    except Exception as exc:
        return {'error': type(exc).__name__, 'detail': str(exc)[:160]}


def safe_preview(value):
    if isinstance(value, dict):
        return {'type': 'object', 'keys': list(value.keys())[:40]}
    if isinstance(value, list):
        return {'type': 'array', 'length': len(value), 'first_item_keys': list(value[0].keys())[:30] if value and isinstance(value[0], dict) else []}
    return {'type': type(value).__name__}


def find_records(value, depth=0):
    """Find likely article arrays without assuming a single API schema."""
    if depth > 5:
        return []
    found = []
    if isinstance(value, list):
        dicts = [item for item in value if isinstance(item, dict)]
        if dicts and any(any(k.lower() in {'title', 'name', 'article_title', 'post_title'} for k in item) for item in dicts):
            found.extend(dicts[:30])
        for item in value[:10]:
            found.extend(find_records(item, depth + 1))
    elif isinstance(value, dict):
        for child in value.values():
            if isinstance(child, (dict, list)):
                found.extend(find_records(child, depth + 1))
    return found


def article_summary(item):
    title = next((item.get(k) for k in ('title', 'name', 'article_title', 'post_title') if isinstance(item.get(k), str)), '')
    date = next((item.get(k) for k in ('publishTime', 'publish_time', 'published_at', 'date', 'createdAt', 'created_at') if isinstance(item.get(k), (str, int, float))), None)
    link = next((item.get(k) for k in ('url', 'link', 'path', 'slug') if isinstance(item.get(k), str)), None)
    return {'title': title[:180], 'date_field': date, 'link_field': link[:250] if link else None}


def main():
    probes = []
    # Keep the request count small; only read the public bulletin listing endpoint.
    cases = [
        ('base_query', '/api/bulletin', {'lang': 'ja-jp', 'code': APP_CODE, 'page': '1', 'pageSize': '20', 'tabs': ''}),
        ('tabs_zero', '/api/bulletin', {'lang': 'ja-jp', 'code': APP_CODE, 'page': '1', 'pageSize': '20', 'tabs': '0'}),
        ('tabs_all', '/api/bulletin', {'lang': 'ja-jp', 'code': APP_CODE, 'page': '1', 'pageSize': '20', 'tabs': 'all'}),
        ('slash_base_query', '/api/bulletin/', {'lang': 'ja-jp', 'code': APP_CODE, 'page': '1', 'pageSize': '20', 'tabs': ''}),
    ]
    for name, path, params in cases:
        url = HOST + path + '?' + urllib.parse.urlencode(params)
        response = fetch(url)
        item = {'case': name, 'url': url, 'status': response.get('status'), 'content_type': response.get('content_type'), 'error': response.get('error')}
        if 'json' in response:
            data = response['json']
            item['json_shape'] = safe_preview(data)
            if isinstance(data, dict):
                item['top_level_keys'] = list(data.keys())[:40]
            records = find_records(data)
            unique = []
            seen = set()
            for record in records:
                summary = article_summary(record)
                if summary['title'] and summary['title'] not in seen:
                    seen.add(summary['title'])
                    unique.append(summary)
            item['article_preview'] = unique[:12]
        elif response.get('body'):
            item['body_preview'] = re.sub(r'\s+', ' ', response['body'][:300])
        elif response.get('body_preview'):
            item['body_preview'] = response['body_preview']
        if response.get('detail'):
            item['detail'] = response['detail']
        probes.append(item)

    successful = [p for p in probes if p.get('status') == 200 and p.get('json_shape', {}).get('type') in ('object', 'array')]
    report = {
        'version': 84,
        'mode': 'read_only',
        'host': HOST,
        'app_code': APP_CODE,
        'probe_count': len(probes),
        'probes': probes,
        'json_endpoint_success': bool(successful),
        'successful_cases': [p['case'] for p in successful],
        'event_modifications': 0,
        'warning': 'Public GET diagnostics only. No event data was added or changed; API response fields and article previews require verification.'
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('V84 API probes:', len(probes), 'JSON endpoint success:', bool(successful), 'report:', OUT)

if __name__ == '__main__':
    main()
