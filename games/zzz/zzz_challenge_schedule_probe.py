#!/usr/bin/env python3
"""Read-only ZZZ HoYoLAB challenge schedule discovery. Never edits events.json.

Run: python games/zzz/zzz_challenge_schedule_probe.py
"""
import argparse
import json
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LIST = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList'
DETAIL = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; EventCalendarProbe/1.0)', 'Accept': 'application/json'}
CHALLENGE = re.compile(r'Shiyu Defense|Critical Node|Deadly Assault|式輿防衛戦|危局強襲戦|激変ノード|危局强袭战|式舆防卫战', re.I)
DATE = re.compile(r'(?:20\d{2}[/.-]\d{1,2}[/.-]\d{1,2}|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}\b|\d{1,2}:\d{2}|reset|refresh|rotation|season|phase|period|更新|刷新|轮换)', re.I)
EXPLICIT_DATE = re.compile(r'20\d{2}[/.-]\d{1,2}[/.-]\d{1,2}|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}\b', re.I)


def get_json(url):
    with urlopen(Request(url, headers=HEADERS), timeout=25) as resp:
        obj = json.load(resp)
    if obj.get('retcode', 0) not in (0, None):
        raise RuntimeError(f"API retcode {obj.get('retcode')}: {obj.get('message')}")
    return obj.get('data') or obj


def collect_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for x in value:
            yield from collect_strings(x)
    elif isinstance(value, dict):
        for k, v in value.items():
            if k in ('insert', 'text', 'content', 'structured_content', 'desc', 'description'):
                yield from collect_strings(v)
            elif isinstance(v, (dict, list)):
                yield from collect_strings(v)


def full_text(detail):
    post = detail.get('post') or {}
    if isinstance(post, dict):
        post = post.get('post') or post
    segments = []
    for root in (post, detail):
        if not isinstance(root, dict):
            continue
        for key in ('structured_content', 'content', 'desc'):
            raw = root.get(key)
            if isinstance(raw, str) and raw.lstrip().startswith(('{', '[')):
                try:
                    raw = json.loads(raw)
                except ValueError:
                    pass
            segments.extend(collect_strings(raw))
    text = ' '.join(segments)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text)).strip()


def excerpts(text, pattern, radius=200, max_count=6):
    spans = []
    for match in pattern.finditer(text):
        left, right = max(0, match.start()-radius), min(len(text), match.end()+radius)
        if spans and left <= spans[-1][1]:
            spans[-1] = (spans[-1][0], max(spans[-1][1], right))
        else:
            spans.append((left, right))
    return [text[a:b][:650] for a, b in spans[:max_count]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=50, help='articles per news category, max 50')
    parser.add_argument('--max-details', type=int, default=150, help='maximum article bodies to fetch')
    args = parser.parse_args()
    if not 1 <= args.limit <= 50 or args.max_details < 1:
        parser.error('limit must be 1..50 and max-details >= 1')
    articles = {}
    for kind in (1, 2, 3):
        try:
            data = get_json(LIST + '?' + urlencode({'gids': 8, 'type': kind, 'page_size': args.limit}))
            items = data.get('list') or []
            print(f'NEWS TYPE {kind}: {len(items)} articles')
            for item in items:
                post = item.get('post', item) if isinstance(item, dict) else {}
                pid = str(post.get('post_id') or post.get('id') or '')
                if pid.isdigit():
                    articles.setdefault(pid, str(post.get('subject') or post.get('title') or ''))
        except Exception as exc:
            print(f'WARNING NEWS TYPE {kind}: {exc}')
    print(f'UNIQUE ARTICLES: {len(articles)}; checking up to {args.max_details} bodies')
    checked = matched = candidates = errors = 0
    for pid, title in list(articles.items())[:args.max_details]:
        try:
            body = full_text(get_json(DETAIL + '?' + urlencode({'post_id': pid})))
            checked += 1
        except Exception as exc:
            errors += 1
            print(f'ERROR {pid}: {exc}')
            continue
        if not CHALLENGE.search(title + ' ' + body):
            continue
        matched += 1
        # An explicit calendar date must occur near a challenge mention, not just in update/compensation text.
        contexts = excerpts(body, CHALLENGE, radius=260, max_count=12)
        relevant = [s for s in contexts if EXPLICIT_DATE.search(s)]
        print(f'\nMATCH: {title}\nURL: https://www.hoyolab.com/article/{pid}')
        print(f'CHALLENGE MENTIONS: {len(list(CHALLENGE.finditer(body)))}; NEARBY EXPLICIT-DATE CONTEXTS: {len(relevant)}')
        if relevant:
            candidates += 1
            for s in relevant[:4]:
                print('POSSIBLE DATE CONTEXT:', s)
        else:
            for s in contexts[:2]:
                print('CHALLENGE CONTEXT:', s[:420])
        time.sleep(0.05)
    print(f'\nSUMMARY: checked={checked}, challenge_articles={matched}, date_context_candidates={candidates}, request_errors={errors}')
    print('PREVIEW ONLY: dates near challenge names are leads, NOT verified schedule windows. No files modified.')


if __name__ == '__main__':
    main()
