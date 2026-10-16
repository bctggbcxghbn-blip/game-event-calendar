#!/usr/bin/env python3
"""Read-only Genshin event/wish/challenge discovery across HoYoLAB news types.

No events.json writes. Uses existing HSR HoYoLAB helpers. Prints compact evidence
for the next parser iteration; never assumes timezone for unlabeled timestamps.
"""
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'games' / 'hsr'))
from hsr_maintenance_detail_probe import LIST, DETAIL, get_json  # noqa: E402
from hsr_maintenance_time_preview import content_text  # noqa: E402

WISH = re.compile(r'event wishes? notice|event wish(?:es)?\b|祈願|祈愿|祈願情報', re.I)
CHALLENGE = re.compile(r'spiral abyss|imaginarium theater|stygian onslaught|深境螺旋|幻想シアター|幻想真境劇詩|幽境の激戦', re.I)
EVENT = re.compile(r'events? preview|event[:：]|web event|login event|イベント|活动|double drops|overflowing', re.I)
DATE = re.compile(r'20\d{2}[/-]\d{1,2}[/-]\d{1,2}(?:\s+\d{1,2}:\d{2})?(?:\s*\(?\s*(?:UTC|GMT)\s*\+\s*8\s*\)?)?', re.I)
SECTION = re.compile(r'(?:event wish duration|event duration|event time|challenge duration|duration|開催期間|活动时间)', re.I)

def category(title):
    if WISH.search(title):
        return 'ガチャ'
    if CHALLENGE.search(title):
        return 'チャレンジ'
    if EVENT.search(title):
        return 'イベント'
    return None

def fetch_list(news_type, limit):
    url = LIST + '?' + urlencode({'gids': '2', 'type': str(news_type), 'page_size': str(limit)})
    result = get_json(url)
    items = result.get('list') if isinstance(result, dict) else None
    if not isinstance(items, list):
        raise ValueError(f'Unexpected response for type={news_type}')
    return items

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--details', type=int, default=15, help='Maximum matching article bodies to inspect')
    args = parser.parse_args()
    if not 1 <= args.limit <= 50 or not 0 <= args.details <= 50:
        parser.error('--limit must be 1..50 and --details 0..50')
    seen = set()
    candidates = []
    for news_type in (1, 2, 3):
        try:
            items = fetch_list(news_type, args.limit)
            print(f'NEWS TYPE {news_type}: {len(items)} articles', flush=True)
        except Exception as exc:
            print(f'WARNING TYPE {news_type}: {type(exc).__name__}: {str(exc)[:160]}', flush=True)
            continue
        for item in items:
            post = item.get('post', item) if isinstance(item, dict) else {}
            if not isinstance(post, dict):
                continue
            pid = str(post.get('post_id') or post.get('id') or '')
            title = str(post.get('subject') or post.get('title') or '')
            if not pid.isdigit() or pid in seen:
                continue
            seen.add(pid)
            kind = category(title)
            if kind:
                candidates.append((pid, title, kind, news_type))
    counts = {k: sum(c[2] == k for c in candidates) for k in ('イベント', 'ガチャ', 'チャレンジ')}
    print(f'FOUND {len(candidates)} unique candidate articles: {counts}', flush=True)
    # Prefer wish and challenge examples when sampling details.
    priority = {'ガチャ': 0, 'チャレンジ': 1, 'イベント': 2}
    for pid, title, kind, news_type in sorted(candidates, key=lambda x: priority[x[2]])[:args.details]:
        print(f'\nARTICLE [{kind}] type={news_type} id={pid}: {title[:150]}', flush=True)
        print(f'URL https://www.hoyolab.com/article/{pid}', flush=True)
        try:
            detail = get_json(DETAIL + '?' + urlencode({'post_id': pid}))
            body = content_text(detail)
            print(f'BODY LENGTH {len(body)}', flush=True)
            contexts = []
            for match in SECTION.finditer(body):
                contexts.append(body[max(0, match.start()-45):match.start()+230].replace('\n', ' '))
                if len(contexts) >= 3:
                    break
            if not contexts:
                for match in DATE.finditer(body):
                    contexts.append(body[max(0, match.start()-50):match.end()+100].replace('\n', ' '))
                    if len(contexts) >= 3:
                        break
            if not contexts:
                print('NO DATE OR DURATION CONTEXT', flush=True)
            for context in contexts:
                print('CONTEXT ' + re.sub(r'\s+', ' ', context)[:275], flush=True)
        except Exception as exc:
            print(f'WARNING DETAIL {pid}: {type(exc).__name__}: {str(exc)[:150]}', flush=True)
    print('\nPREVIEW ONLY. No files modified.', flush=True)

if __name__ == '__main__':
    main()
