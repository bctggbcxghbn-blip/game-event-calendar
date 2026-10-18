#!/usr/bin/env python3
"""V32: discover linked official schedule sources in official news article bodies (read only).
No writes, no guessed endpoints, no automatic time promotion.
Requires wuwa_dynamic_gacha_preview_v26.py alongside this file.
"""
import argparse
import html
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wuwa_dynamic_gacha_preview_v26 as v26

URL_RE = re.compile(r'https?://[^\s<>"\'\\]+', re.I)
HREF_RE = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.I)
SCHEDULE_RE = re.compile(r'日程|スケジュール|開催期間|開催時間|集音|ガチャ|イベント|カレンダー|schedule|calendar|timeline|banner', re.I)
OFFICIAL_RE = re.compile(r'(?:^|\.)(?:kurogames\.com|kurogame\.com|kurogame\.net|wutheringwaves\.com)$', re.I)

def clean_url(raw):
    s = html.unescape(raw).strip().rstrip('.,;)]}、。')
    if s.startswith('//'):
        s = 'https:' + s
    p = urlparse(s)
    if p.scheme not in ('http', 'https') or not p.netloc:
        return None
    return s

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--days-back', type=int, default=180)
    ap.add_argument('--article-limit', type=int, default=120)
    ap.add_argument('--show-limit', type=int, default=80)
    args = ap.parse_args()
    print('WUWA V32 OFFICIAL LINKED SCHEDULE SOURCE PROBE / READ ONLY')
    print('No events.json writes. Links are discoveries, not confirmed schedule sources.')
    items = v26.discover(args.days_back)
    selected = [x for x in items if re.search(r'集音|イベント|Ver\.?|バージョン|アップデート|開催|お知らせ|予告', x.get('title',''), re.I)][:max(0,args.article_limit)]
    print('ARTICLES_TO_INSPECT:', len(selected))
    seen = {}
    errors = 0
    for item in selected:
        try:
            content = v26.body(item['id'])
            raw = str(content)
        except Exception as exc:
            errors += 1
            print('FETCH_ERROR:', item['id'], type(exc).__name__, str(exc)[:100])
            continue
        for candidate in URL_RE.findall(raw) + HREF_RE.findall(raw):
            u = clean_url(candidate)
            if not u:
                continue
            parsed = urlparse(u)
            host = parsed.hostname or ''
            if not OFFICIAL_RE.search(host):
                continue
            # Exclude image/video/static assets and the source article itself.
            if re.search(r'\.(?:png|jpe?g|webp|gif|svg|mp4|webm|woff2?|ttf)(?:$|\?)', parsed.path, re.I):
                continue
            if not SCHEDULE_RE.search(unquote(u)):
                continue
            seen.setdefault(u, set()).add(str(item['id']))
    print('FETCH_ERRORS:', errors, 'POTENTIAL_OFFICIAL_LINKS:', len(seen))
    for url, ids in list(sorted(seen.items(), key=lambda kv: (-len(kv[1]), kv[0])))[:max(0,args.show_limit)]:
        print('LINK_CANDIDATE', 'ARTICLES='+','.join(sorted(ids)), 'URL='+url)
    if not seen:
        print('NO_LINKED_SCHEDULE_SOURCE_FOUND: articles may use embedded images, scripts or unlinked pages')
    print('SUMMARY: INSPECTED='+str(len(selected))+' LINK_CANDIDATES='+str(len(seen))+' FETCH_ERRORS='+str(errors)+' READ_ONLY=true')
    print('NEXT: inspect candidate URLs manually; never treat links or maintenance estimates as confirmed times.')

if __name__ == '__main__':
    main()
