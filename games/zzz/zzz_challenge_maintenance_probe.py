#!/usr/bin/env python3
"""Preview official ZZZ challenge/maintenance announcements; never edits files."""
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'games' / 'hsr'))
from hsr_maintenance_detail_probe import DETAIL, LIST, get_json
from hsr_maintenance_time_preview import content_text

PATTERNS = {
    'チャレンジ': re.compile(r'shiyu\s*defen[sc]e|deadly\s*assault|hollow\s*zero|lost\s*void|式輿防衛戦|危局強襲戦|零号ホロウ|式舆防卫战|危局强袭战', re.I),
    'メンテナンス': re.compile(r'maintenance|version\s*\d+(?:\.\d+)?\s*update|update\s*notice|メンテナンス|アップデートのお知らせ|维护|停服|版本更新', re.I),
}
DATE = re.compile(r'20\d{2}[/.-]\d{1,2}[/.-]\d{1,2}(?:\s+\d{1,2}:\d{2})?', re.I)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--max-detail', type=int, default=25)
    args = parser.parse_args()
    if not 1 <= args.limit <= 50 or args.max_detail < 1:
        parser.error('--limit must be 1..50 and --max-detail >= 1')
    seen = set()
    candidates = []
    for typ in (1, 2, 3):
        try:
            data = get_json(LIST + '?' + urlencode({'gids': 8, 'type': typ, 'page_size': args.limit}))
            items = data.get('list', [])
            print(f'NEWS TYPE {typ}: {len(items)} articles')
        except Exception as exc:
            print(f'WARNING TYPE {typ}: {exc}')
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
            kinds = [kind for kind, rx in PATTERNS.items() if rx.search(title)]
            if kinds:
                candidates.append((pid, title, kinds))
    print(f'TITLE CANDIDATES: {len(candidates)}')
    for pid, title, kinds in candidates[:args.max_detail]:
        print(f'\nARTICLE [{", ".join(kinds)}] id={pid}: {title}')
        print(f'URL https://www.hoyolab.com/article/{pid}')
        try:
            body = content_text(get_json(DETAIL + '?' + urlencode({'post_id': pid})))
            print(f'BODY LENGTH: {len(body)}')
            dates = list(DATE.finditer(body))
            if dates:
                for match in dates[:6]:
                    start, end = max(0, match.start()-100), min(len(body), match.end()+130)
                    print('DATE CONTEXT:', ' '.join(body[start:end].split())[:260])
            else:
                print('DATE CONTEXT: No explicit date found')
            body_kinds = [kind for kind, rx in PATTERNS.items() if rx.search(body)]
            print('BODY KEYWORDS:', ', '.join(body_kinds) or 'none')
        except Exception as exc:
            print(f'WARNING DETAIL: {type(exc).__name__}: {exc}')
    print('\nPREVIEW ONLY. No files modified.')

if __name__ == '__main__':
    main()
