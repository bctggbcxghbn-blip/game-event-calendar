#!/usr/bin/env python3
"""Zenless Zone Zero HoYoLAB official announcement discovery (read-only).

Place at games/zzz/zzz_preview.py. Reuses the existing HSR API helpers.
Does not modify events.json.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'games' / 'hsr'))
from hsr_maintenance_detail_probe import DETAIL, LIST, get_json
from hsr_maintenance_time_preview import content_text

GID = '8'  # Zenless Zone Zero on HoYoLAB
TYPES = (1, 2, 3)
MAX_DETAIL = 18
DATE_MARK = re.compile(r'20\d{2}[/-]\d{1,2}[/-]\d{1,2}|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+20\d{2}', re.I)
PATTERNS = [
    ('ガチャ', re.compile(r'exclusive channel|signal search|channel details|channel notice|変調|独占チャンネル|音動機チャンネル|限定チャンネル|调频|独家频段', re.I)),
    ('チャレンジ', re.compile(r'shiyu defense|deadly assault|hollow zero|simulated battle|式輿防衛戦|危局強襲戦|零号ホロウ|式舆防卫战|危局强袭战', re.I)),
    ('メンテナンス', re.compile(r'maintenance|version update notice|update maintenance|メンテナンス|アップデート予告|维护|停服', re.I)),
    ('イベント', re.compile(r'event|login|limited.time|web event|イベント|ログイン|活动|签到', re.I)),
]

def classify(title):
    for label, regex in PATTERNS:
        if regex.search(title):
            return label
    return None

def get_articles(kind):
    params = urlencode({'gids': GID, 'type': kind, 'page_size': 50})
    data = get_json(LIST + '?' + params)
    if not isinstance(data, dict) or not isinstance(data.get('list'), list):
        raise ValueError('Unexpected response format')
    return data['list']

def main():
    seen = set()
    found = []
    for news_type in TYPES:
        try:
            items = get_articles(news_type)
        except Exception as exc:
            print(f'NEWS TYPE {news_type}: ERROR {type(exc).__name__}: {exc}')
            continue
        print(f'NEWS TYPE {news_type}: {len(items)} articles')
        for item in items:
            if not isinstance(item, dict):
                continue
            post = item.get('post', item)
            if not isinstance(post, dict):
                continue
            pid = str(post.get('post_id') or post.get('id') or '')
            title = str(post.get('subject') or post.get('title') or '')
            if not pid.isdigit() or pid in seen:
                continue
            seen.add(pid)
            label = classify(title)
            if label:
                found.append((pid, title, label, news_type))
    print(f'FOUND {len(found)} candidate articles: {dict(Counter(x[2] for x in found))}')
    for pid, title, label, news_type in found[:MAX_DETAIL]:
        print(f'ARTICLE [{label}] type={news_type} id={pid}: {title}')
        print(f'URL https://www.hoyolab.com/article/{pid}')
        try:
            detail = get_json(DETAIL + '?' + urlencode({'post_id': pid}))
            outer = detail.get('post', {}) if isinstance(detail, dict) else {}
            post = outer.get('post', outer) if isinstance(outer, dict) else {}
            gid = post.get('game_id') if isinstance(post, dict) else None
            if gid is not None and str(gid) != GID:
                print(f'WARNING game_id={gid}, expected {GID}')
            body = content_text(detail)
            print(f'BODY LENGTH {len(body)}')
            matches = list(DATE_MARK.finditer(body))
            if not matches:
                print('CONTEXT no dated text found')
            for match in matches[:3]:
                excerpt = ' '.join(body[max(0, match.start()-85):match.end()+180].split())
                print(f'CONTEXT {excerpt[:270]}')
        except Exception as exc:
            print(f'DETAIL ERROR {type(exc).__name__}: {str(exc)[:160]}')
    print('PREVIEW ONLY. No files modified.')

if __name__ == '__main__':
    main()
