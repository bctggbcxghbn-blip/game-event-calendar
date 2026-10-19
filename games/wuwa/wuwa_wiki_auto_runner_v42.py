#!/usr/bin/env python3
"""V42: prioritize newest linked versions with shorter index cache and safe retries.
Requires V35 parser and V40 importer. Dry-run by default.
"""
import argparse
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
BASE = 'https://wikiwiki.jp/w-w/'
VERSION = re.compile(r'^Ver(\d+)\.(\d+)$')
INDEXES = ('', '集音')
JST = timezone(timedelta(hours=9))

class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if href:
                self.hrefs.append(href)

def linked_version(href):
    url = urllib.parse.urljoin(BASE, href)
    p = urllib.parse.urlparse(url)
    if p.scheme != 'https' or p.netloc != 'wikiwiki.jp':
        return None
    path = urllib.parse.unquote(p.path).rstrip('/')
    if not path.startswith('/w-w/'):
        return None
    name = path[len('/w-w/'):]
    return name if VERSION.fullmatch(name) else None

def fetch(page, cache_dir, ttl_hours, fixture_dir=None, retries=2, pause=3):
    key = 'index' if page == '' else re.sub(r'[^a-zA-Z0-9_.-]', '_', page)
    # Hash prevents collisions for Japanese names and index labels.
    import hashlib
    key += '-' + hashlib.sha256(page.encode()).hexdigest()[:12]
    target = cache_dir / (key + '.html')
    if fixture_dir is not None:
        fixture = fixture_dir / (key + '.html')
        if not fixture.exists():
            raise FileNotFoundError('missing fixture ' + str(fixture))
        return fixture.read_text(encoding='utf-8'), 'FIXTURE'
    if target.exists() and time.time() - target.stat().st_mtime <= ttl_hours * 3600:
        return target.read_text(encoding='utf-8'), 'CACHE_HIT'
    url = BASE + urllib.parse.quote(page, safe='/')
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; GameEventCalendar/1.0)', 'Accept': 'text/html'})
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read().decode('utf-8', 'replace')
            if len(raw) < 500:
                raise ValueError('HTML too short')
            cache_dir.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix('.tmp')
            tmp.write_text(raw, encoding='utf-8')
            tmp.replace(target)
            return raw, 'FETCH_OK'
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                print('RATE_LIMIT HTTP_429 page=' + (page or '(top)') + ' attempt=' + str(attempt+1), flush=True)
                if attempt < retries:
                    time.sleep(pause * (2 ** attempt))
                    continue
                raise RuntimeError('HTTP_429: abort; stale cache never used for apply') from exc
            if exc.code in (500, 502, 503, 504) and attempt < retries:
                time.sleep(pause * (2 ** attempt))
                continue
            raise
        except (OSError, TimeoutError):
            if attempt < retries:
                time.sleep(pause * (2 ** attempt))
                continue
            raise

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--events', default='events.json')
    p.add_argument('--cache-dir', default='.cache/wuwa-wiki')
    p.add_argument('--ttl-hours', type=float, default=24)
    p.add_argument('--index-ttl-hours', type=float, default=6)
    p.add_argument('--max-versions', type=int, default=2)
    p.add_argument('--seed-version', default='Ver3.7')
    p.add_argument('--fixture-dir', type=Path, help='Offline test fixtures named like cache entries')
    p.add_argument('--retries', type=int, default=2)
    p.add_argument('--pause', type=float, default=3)
    args = p.parse_args()
    if not 1 <= args.max_versions <= 8 or not VERSION.fullmatch(args.seed_version) or not 0 < args.ttl_hours <= 168 or not 0 < args.index_ttl_hours <= 168 or not 0 <= args.retries <= 3 or not 0 <= args.pause <= 60:
        p.error('invalid limits')
    for dep in ('wuwa_wiki_merge_preview_v35.py', 'wuwa_wiki_gacha_import_v40.py'):
        if not (HERE / dep).is_file():
            print('ERROR MISSING_DEPENDENCY', dep)
            return 2
    events_path = Path(args.events).resolve()
    try:
        before = json.loads(events_path.read_text(encoding='utf-8'))
        if not isinstance(before, list):
            raise ValueError('events.json must be array')
    except Exception as exc:
        print('ERROR EVENTS', repr(exc)); return 2
    spec = importlib.util.spec_from_file_location('wuwa_v35_for_v41', HERE / 'wuwa_wiki_merge_preview_v35.py')
    v35 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v35)
    mode = 'APPLY' if args.apply else 'DRY_RUN'
    print('WUWA V42 NEWEST-FIRST WIKI RUNNER MODE=' + mode, flush=True)
    print('CACHE_TTL: indexes=%sh version_pages=%sh' % (args.index_ttl_hours, args.ttl_hours), flush=True)
    print('BEFORE:', len(before), 'INDEXES:', len(INDEXES), 'MAX_VERSIONS:', args.max_versions, flush=True)
    cache = Path(args.cache_dir)
    found = {args.seed_version}
    ok = 0
    # Fail closed if an index fetch fails; do not silently miss new versions.
    for page in INDEXES:
        try:
            raw, source = fetch(page, cache, args.index_ttl_hours, args.fixture_dir, args.retries, args.pause)
            links = Links(); links.feed(raw)
            new = {v for href in links.hrefs if (v := linked_version(href))}
            found.update(new)
            ok += 1
            print('INDEX_OK', page or '(top)', source, 'VERSION_LINKS=', len(new), flush=True)
        except Exception as exc:
            print('STOP INDEX_ERROR', page or '(top)', repr(exc), 'NO_WRITES', flush=True)
            return 3
    ordered = sorted(found, key=lambda v: tuple(map(int, VERSION.fullmatch(v).groups())), reverse=True)
    print('DISCOVERED_LINK_VERSIONS:', ','.join(ordered), flush=True)
    print('PRIORITY_LATEST:', ','.join(ordered[:args.max_versions]), flush=True)
    ready = []
    for version in ordered[:args.max_versions]:
        try:
            raw, source = fetch(version, cache, args.ttl_hours, args.fixture_dir, args.retries, args.pause)
            records, holds = v35.get_rows(raw, version)
            if holds:
                print('STOP PARSE_HOLD', version, holds[:3], 'NO_WRITES', flush=True)
                return 4
            if not records:
                print('STOP NO_SCHEDULE', version, 'NO_WRITES', flush=True)
                return 4
            ready.append((version, raw))
            print('READY', version, source, 'ROWS=', len(records), flush=True)
        except Exception as exc:
            print('STOP VERSION_ERROR', version, repr(exc), 'NO_WRITES', flush=True)
            return 4
    # All network fetching and validation completed BEFORE any importer is allowed to write.
    for version, raw in ready:
        with tempfile.TemporaryDirectory(prefix='wuwa-v41-') as tmp:
            file = Path(tmp) / 'page.html'
            file.write_text(raw, encoding='utf-8')
            cmd = [sys.executable, str(HERE / 'wuwa_wiki_gacha_import_v40.py'), '--version', version, '--events', str(events_path), '--html-file', str(file)]
            if args.apply:
                cmd.append('--apply')
            print('RUN_V40', version, 'MODE=' + mode, flush=True)
            rc = subprocess.run(cmd, check=False).returncode
            if rc:
                print('ERROR IMPORT', version, rc, flush=True)
                return rc
    try:
        after = json.loads(events_path.read_text(encoding='utf-8'))
        if not isinstance(after, list) or (not args.apply and after != before) or len(after) < len(before):
            raise ValueError('unexpected events.json change')
    except Exception as exc:
        print('ERROR VERIFY', repr(exc)); return 5
    print('SUMMARY: INDEX_OK=%d DISCOVERED=%d READY=%d BEFORE=%d AFTER=%d MODE=%s' % (ok, len(found), len(ready), len(before), len(after), mode))
    print('NOTE: Index HTML cached 6h and version HTML 24h by default; Wiki dates are unverified date-only; unlinked versions may be missed.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
