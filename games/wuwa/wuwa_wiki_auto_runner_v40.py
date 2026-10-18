#!/usr/bin/env python3
"""V40: discover Wuwa Wiki version pages from index links; delegate to V40 importer.
Dry-run by default. Standard library only. Requires V35/V36 beside this script.
"""
import argparse
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
BASE = 'https://wikiwiki.jp/w-w/'
V35 = HERE / 'wuwa_wiki_merge_preview_v35.py'
V36 = HERE / 'wuwa_wiki_gacha_import_v40.py'
INDEXES = ('', '集音/履歴', '集音', 'Ver3.7')
VERSION = re.compile(r'^Ver(\d+)\.(\d+)$')

class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if href:
                self.hrefs.append(href)

def version_from_link(href):
    url = urllib.parse.urljoin(BASE, href)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.netloc != 'wikiwiki.jp':
        return None
    path = urllib.parse.unquote(parsed.path).rstrip('/')
    if not path.startswith('/w-w/'):
        return None
    tail = path[len('/w-w/'):]
    if '/' in tail or not VERSION.fullmatch(tail):
        return None
    return tail

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 WuwaCalendar/1.0'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read().decode('utf-8', 'replace')

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--events', default='events.json')
    ap.add_argument('--max-versions', type=int, default=4)
    ap.add_argument('--seed-version', default='Ver3.7')
    args = ap.parse_args()
    if not 1 <= args.max_versions <= 12 or not VERSION.fullmatch(args.seed_version):
        ap.error('invalid max-versions (1..12) or seed-version')
    if not V35.is_file() or not V36.is_file():
        print('ERROR: V35 and V36 must be beside V38')
        return 2
    events_path = Path(args.events).resolve()
    try:
        before = json.loads(events_path.read_text(encoding='utf-8'))
        if not isinstance(before, list):
            raise ValueError('events.json must be an array')
    except Exception as exc:
        print('ERROR EVENTS', repr(exc))
        return 2
    spec = importlib.util.spec_from_file_location('wuwa_v35_v38', V35)
    v35 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v35)
    print('WUWA V40 PERIOD-AWARE WIKI VERSION RUNNER MODE=' + ('APPLY' if args.apply else 'DRY_RUN'), flush=True)
    print('DATE_ONLY_UNVERIFIED: Wiki date-only entries; official entries never overwritten', flush=True)
    print('BEFORE:', len(before), 'INDEXES:', len(INDEXES), flush=True)
    found = {args.seed_version}
    successful_indexes = 0
    for page in INDEXES:
        try:
            raw = fetch(BASE + urllib.parse.quote(page, safe='/'))
            links = Links(); links.feed(raw)
            new = {v for h in links.hrefs if (v := version_from_link(h))}
            found.update(new)
            successful_indexes += 1
            print('INDEX_OK', page or '(top)', 'VERSION_LINKS=', len(new), flush=True)
        except Exception as exc:
            print('INDEX_WARNING', page or '(top)', repr(exc), flush=True)
    if not successful_indexes:
        print('ERROR: no index pages accessible; refusing apply')
        return 3
    ordered = sorted(found, key=lambda v: tuple(map(int, VERSION.fullmatch(v).groups())), reverse=True)
    print('DISCOVERED_LINK_VERSIONS:', ','.join(ordered), flush=True)
    ready = []
    for version in ordered[:args.max_versions]:
        try:
            raw = fetch(BASE + version)
            records, holds = v35.get_rows(raw, version)
            if holds:
                print('HOLD PARSE', version, 'COUNT=', len(holds), 'DETAIL=', holds[:3], flush=True)
                continue
            if not records:
                print('HOLD NO_SCHEDULE', version, flush=True)
                continue
            print('READY', version, 'ROWS=', len(records), flush=True)
            ready.append((version, raw))
        except Exception as exc:
            print('VERSION_WARNING', version, repr(exc), flush=True)
    for version, raw in ready:
        with tempfile.TemporaryDirectory(prefix='wuwa-v39-') as tmp:
            html_file = Path(tmp) / 'wiki.html'
            html_file.write_text(raw, encoding='utf-8')
            cmd = [sys.executable, str(V36), '--version', version, '--events', str(events_path), '--html-file', str(html_file)]
            if args.apply:
                cmd.append('--apply')
            print('RUN_V40', version, 'MODE=' + ('APPLY' if args.apply else 'DRY_RUN'), flush=True)
            result = subprocess.run(cmd, check=False)
            if result.returncode:
                print('ERROR V39', version, 'EXIT=', result.returncode)
                return result.returncode
    try:
        after = json.loads(events_path.read_text(encoding='utf-8'))
    except Exception as exc:
        print('ERROR AFTER', repr(exc))
        return 5
    if not args.apply and before != after:
        print('ERROR DRY_RUN_MODIFIED_EVENTS')
        return 5
    print('SUMMARY: INDEX_OK=%d DISCOVERED=%d READY=%d BEFORE=%d AFTER=%d MODE=%s' %
          (successful_indexes, len(found), len(ready), len(before), len(after), 'APPLY' if args.apply else 'DRY_RUN'))
    print('NOTE: Index discovery depends on Wiki links; unlinked future pages are not detected.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
