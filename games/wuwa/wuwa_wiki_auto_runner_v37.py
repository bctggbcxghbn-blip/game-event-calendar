#!/usr/bin/env python3
"""V37: Discover sequential Wuwa Wiki version schedules, delegate safe imports to V36.
Dry run by default. Requires V35 and V36 alongside this file. Standard library only.
"""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
V35 = HERE / 'wuwa_wiki_merge_preview_v35.py'
V36 = HERE / 'wuwa_wiki_gacha_import_v36.py'
BASE = 'https://wikiwiki.jp/w-w/'


def version_sequence(start, count):
    m = re.fullmatch(r'Ver(\d+)\.(\d+)', start)
    if not m:
        raise ValueError('start version must look like Ver3.7')
    major, minor = map(int, m.groups())
    for _ in range(count):
        yield f'Ver{major}.{minor}'
        minor += 1
        if minor >= 10:
            major, minor = major + 1, 0


def fetch(version):
    request = urllib.request.Request(BASE + version, headers={'User-Agent': 'Mozilla/5.0 WuwaCalendar/1.0'})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode('utf-8', 'replace')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--start-version', default='Ver3.7')
    p.add_argument('--max-probe', type=int, default=8)
    p.add_argument('--events', default='events.json')
    args = p.parse_args()
    if not 1 <= args.max_probe <= 20:
        p.error('--max-probe must be between 1 and 20')
    if not V35.exists() or not V36.exists():
        print('ERROR: V35 and V36 scripts must be in games/wuwa/')
        return 2
    spec = importlib.util.spec_from_file_location('wuwa_v35_v37', V35)
    v35 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v35)
    events_file = Path(args.events)
    try:
        before = json.loads(events_file.read_text(encoding='utf-8'))
        if not isinstance(before, list):
            raise ValueError('events.json must be a list')
    except Exception as exc:
        print('ERROR EVENTS:', repr(exc))
        return 2
    print('WUWA V37 AUTO WIKI VERSION RUNNER MODE=' + ('APPLY' if args.apply else 'DRY_RUN'))
    print('DATE_ONLY_UNVERIFIED: Wiki dates have no confirmed timezone; official entries not overwritten')
    print('BEFORE:', len(before), 'START:', args.start_version, 'MAX_PROBE:', args.max_probe)
    discovered = []
    consecutive_missing = 0
    for version in version_sequence(args.start_version, args.max_probe):
        try:
            html = fetch(version)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                print('NOT_FOUND', version)
                consecutive_missing += 1
                if consecutive_missing >= 2:
                    print('STOP: two consecutive missing versions')
                    break
                continue
            print('FETCH_ERROR', version, repr(exc))
            return 3
        except Exception as exc:
            print('FETCH_ERROR', version, repr(exc))
            return 3
        records, holds = v35.get_rows(html, version)
        if not records or holds:
            print('NOT_READY', version, 'ROWS=', len(records), 'HOLDS=', len(holds))
            if holds:
                for hold in holds[:8]:
                    print('PARSE_HOLD', version, *hold)
                # Never import a partially parsed version.
                return 4
            consecutive_missing += 1
            if consecutive_missing >= 2:
                print('STOP: two consecutive versions without a usable schedule')
                break
            continue
        consecutive_missing = 0
        print('DISCOVERED', version, 'ROWS=', len(records))
        discovered.append((version, html))
    # Run all versions through V36; V36 does duplicate/expiry/short-name checks.
    # Capture HTML once and pass the exact verified version page to V36.
    for version, html in discovered:
        with tempfile.TemporaryDirectory(prefix='wuwa-v37-') as tmp:
            fixture = Path(tmp) / 'wiki.html'
            fixture.write_text(html, encoding='utf-8')
            cmd = [sys.executable, str(V36), '--version', version, '--events', str(events_file), '--html-file', str(fixture)]
            if args.apply:
                cmd.append('--apply')
            print('RUN_V36', version, 'MODE=' + ('APPLY' if args.apply else 'DRY_RUN'), flush=True)
            result = subprocess.run(cmd, check=False)
            if result.returncode:
                print('STOP: V36 failed', version, 'EXIT=', result.returncode)
                return result.returncode
    after = json.loads(events_file.read_text(encoding='utf-8'))
    if not args.apply and before != after:
        print('ERROR: dry run changed events.json')
        return 5
    print('SUMMARY: DISCOVERED=%d BEFORE=%d AFTER=%d MODE=%s' %
          (len(discovered), len(before), len(after), 'APPLY' if args.apply else 'DRY_RUN'))
    if not discovered:
        print('NO_READY_VERSION: no changes')
    return 0

if __name__ == '__main__':
    sys.exit(main())
